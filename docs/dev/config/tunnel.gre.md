(dev-config-tunnel-gre)=
# Configuring GRE Tunnels

This document describes the device data model parameters one should consider when creating a GRE tunnel configuration template. GRE tunnels are implemented as a plugin (`tunnel.gre`) rather than a core module; the plugin uses shared utility functions from the `netsim/extra/tunnel` package.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Overview

The `tunnel.gre` plugin supports point-to-point GRE tunnels with IPv4 or IPv6 transport encapsulation.

**Notes:**

* The configuration template (in Jinja2 format) should be stored in `netsim/extra/tunnel/gre/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details).
* Some devices require an initial configuration template to create the tunnel interface before other modules (e.g., routing) can reference it. Those templates are stored as `<nos>.initial.j2` alongside the main template and are executed during the initial configuration phase.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in intf` in your Jinja2 templates.
* To use GRE tunnels, add `plugin: [ tunnel.gre ]` to the lab topology.

## Data Model

GRE tunnel attributes are defined in `netsim/extra/tunnel/gre/defaults.yml` within the `attributes.link.tunnel` namespace. Every link with `tunnel.mode: gre` becomes a tunnel link.

### Link-Level Attributes (per tunnel)

* **tunnel.mode** (required) -- must be set to `gre`. This is validated by the attribute schema and marks the link as a GRE tunnel.
* **tunnel.af** (optional, string) -- transport address family. Valid values: `ipv4` (default), `ipv6`. Controls whether the tunnel uses regular GRE (`gre`) or IPv6 GRE (`ip6gre`) encapsulation.
* **tunnel.vrf** (optional, string) -- transport VRF name. When set, the tunnel uses a specific VRF to route the GRE packets rather than the global routing table.
* **tunnel.source** (optional, dictionary) -- controls how the tunnel source interface is selected. The system performs an automatic best-effort selection when this attribute is omitted.

### The tunnel.source Dictionary

When `tunnel.source` is specified, it can contain:

* **type** (string) -- source interface type. Currently, only `loopback` is supported as a valid value.
* **linkid** (identifier) -- select the source interface by its [link identifier](link-linkid).
* **link.name** (string) -- select the source interface by its link name.
* **link.role** (string) -- select the source interface by its link role.
* **ifindex** (integer) -- specify the source interface ifindex directly (rarely needed).

### Source Interface Selection

_netlab_ automatically selects the best underlay source interface by iterating over the node's interfaces and applying these filters (in order):

1. If `tunnel.source.type` is not set, interfaces of type `loopback` or `tunnel` are excluded.
2. If `tunnel.vrf` is not set, VRF interfaces are excluded. Otherwise, only interfaces in `tunnel.vrf` VRF are considered.
3. If `tunnel.source.link.name` is set, the interface name must match.
4. If `tunnel.source.linkid` is set, the interface [link identifier](link-linkid) must match.
5. If `tunnel.source.link.role` is set, the interface or its link role must match.
6. If `tunnel.af` is set, only interfaces with a numbered address in that address family are considered.
7. Otherwise, only interfaces with at least one numbered IPv4 or IPv6 address are considered.

The first matching interface is used as the tunnel source.

### Transformed Attributes (set by the plugin)

After the `post_transform` phase, each tunnel interface receives:

* **tunnel.\_source.ifname** (string) -- name of the selected source interface.
* **tunnel.\_source.mtu** (integer) -- MTU of the source interface.
* **tunnel.\_source.ipv4** / **tunnel.\_source.ipv6** (string) -- IP address of the source interface for the tunnel transport AF.
* **tunnel.\_destination.ipv4** / **tunnel.\_destination.ipv6** (string) -- IP address of the remote tunnel endpoint (copied from the neighbor's `tunnel._source`).

The interface also gets:

* **type** set to `tunnel` during `pre_transform`.
* **virtual_interface** set to `True` during link transformation.
* **mtu** (integer) -- the tunnel interface MTU, set during `post_transform` when the user did not specify one. It is calculated as `min(local and remote tunnel._source.mtu)` minus the transport overhead (24 bytes for IPv4 transport, 48 bytes for IPv6 transport).
* An interface description enhanced with `[GRE tunnel]` during `post_transform`.

## Device Features

Device support for GRE tunnels is declared in device YAML files under `features.tunnel.gre`. The feature value is a list of supported capabilities; each device advertises which transport options it supports:

```yaml
features:
  tunnel:
    gre: [ vrf, ipv4, ipv6 ]     # Supports all options
```

Common capability combinations:

| Device | GRE Support |
|---|---|
| FRR | `[ vrf, ipv4, ipv6 ]` |
| Cisco IOS/IOS-XE | `[ vrf, ipv4, ipv6 ]` |
| Arista EOS | `[ ipv4, vrf ]` |
| Mikrotik RouterOS 7 | `[ ipv4, ipv6, vrf ]` |
| Juniper vJunos Router | `[ vrf, ipv4 ]` |
| OpenBSD | `[ ipv4 ]` |

The `check_feature` function in `netsim/extra/tunnel/__init__.py` validates device support by checking for the presence of entries like `ipv4`, `ipv6`, or `vrf` in the device's `features.tunnel.gre` list. If a device does not support the requested feature (e.g., GRE over IPv6 when only `[ipv4]` is listed), an error is reported.

## Tunnel Interface Naming

Tunnel interfaces get `ifindex` values starting at 20000 (the tunnel type is the second entry in `VIRTUAL_INTERFACE_TYPES`, at offset index 1, so `(1 + 1) * 10000 = 20000`).

Each device defines a `tunnel_interface_name` template that controls the tunnel interface name format. Devices that use different names for different tunnel technologies define it as a dictionary keyed by the tunnel mode, for example, FRR uses `gre{ifindex + 1}` for GRE and `wg{ifindex}` for WireGuard tunnels:

| Device | Interface Name Template |
|---|---|
| FRR | `gre{ifindex + 1}` |
| VyOS, Cumulus | `tun{ifindex}` |
| Cisco IOS, Arista EOS | `Tunnel{ifindex}` |
| RouterOS 7 | `tunnel{ifindex}` |
| OpenBSD | `gre{ifindex}` |
| Juniper vJunos Router | `gr-0/0/10.{ifindex}` |
| Juniper vSRX | `gr-0/0/0.{ifindex}` |
| Aruba CX | `tunnel {ifindex}` |

## Containerlab Kernel Modules

When GRE tunnels are used with the `clab` provider, the plugin declares the required kernel modules in `defaults.yml`:

```yaml
providers:
  clab:
    kmods:
      tunnel@gre: [ ip_gre, ip6_gre ]
```

The `@` serves as a dot replacement in module names for kmod lookup. These modules must be loaded on the container host to support GRE tunneling.

## Transformation Process

The plugin hooks into the topology transformation pipeline via two hooks defined in `netsim/extra/tunnel/gre/__init__.py`:

### pre_transform

1. **`_tunnel.set_tunnel_type(topology)`** -- marks all links with `tunnel.mode: gre` as `type: tunnel`.
2. **Validates P2P topology** -- every GRE tunnel link must have exactly two nodes. An error is reported otherwise.

### post_transform

1. **`_p2p.feature_check(topology, ...)`** -- iterates over all nodes, finds those with GRE tunnel interfaces, and validates device feature support (basic GRE, transport AF, and VRF). Calls `api.node_config(ndata, 'tunnel.gre')` for each node that passes all checks.
2. **`_p2p.tunnel_source(topology, node_iflist, ...)`** -- for each node with tunnel interfaces, resolves the source interface using `_tunnel.get_tunnel_source()` and populates `tunnel._source` via `_tunnel.set_tunnel_source()`. Sets `tunnel.af` to `ipv4` as default when not specified.
3. **`_p2p.tunnel_destination(topology, node_iflist, ...)`** -- for each tunnel interface, copies the neighbor's `tunnel._source` to the local `tunnel._destination` and, when the user did not specify the tunnel MTU, computes the interface `mtu` as the minimum of the local and remote source interface MTUs minus the transport overhead (24 bytes for IPv4, 48 bytes for IPv6).

If any errors are detected during source resolution, the destination resolution step is skipped.

## Configuration Templates

### FRR / Linux

Creates GRE or ip6gre tunnels using the `ip tunnel` command. Selects `gre` or `ip6gre` mode based on the `tunnel.af` attribute:

```bash
{%- for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['gre'] %}
{%   set af = intf.tunnel.af|default('ipv4') %}
{%   set gre_mode = 'ip6gre' if af == 'ipv6' else 'gre' %}
ip tunnel add {{ intf.ifname }} mode {{ gre_mode }} \
  local {{ intf.tunnel._source[af] }} remote {{ intf.tunnel._destination[af] }} \
  dev {{ intf.tunnel._source.ifname }} ttl 255
{{ linux_intf_sysctl(intf,role) }}
{% endfor %}
```

### Cisco IOS / IOS-XE

Configures the tunnel mode (gre ip or gre ipv6), optional transport VRF, source interface, and destination address:

```jinja
{% for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['gre'] %}
interface {{ intf.ifname }}
  tunnel mode {{ intf.tunnel.mode }} {{ intf.tunnel.af.replace('ipv4','ip') }}
{%   if intf.tunnel.vrf is defined %}
  tunnel vrf {{ intf.tunnel.vrf }}
{%   endif %}
  tunnel source {{ intf.tunnel._source.ifname }}
  tunnel destination {{ intf.tunnel._destination[intf.tunnel.af] }}
{% endfor %}
```

The `tunnel.af.replace('ipv4','ip')` expression maps `ipv4` to `ip` and leaves `ipv6` as-is, matching IOS syntax.

### VyOS

Requires two templates:

**Initial** (`vyos.initial.j2`) -- creates the tunnel interface with encapsulation, source-address, and remote address:

```jinja
{% for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['gre'] %}
set interfaces tunnel {{ intf.ifname }} encapsulation 'gre'
{%   if intf.tunnel.af == 'ipv6' %}
set interfaces tunnel {{ intf.ifname }} encapsulation 'ip6gre'
{%   endif %}
set interfaces tunnel {{ intf.ifname }} source-address {{ intf.tunnel._source[intf.tunnel.af] }}
set interfaces tunnel {{ intf.ifname }} remote {{ intf.tunnel._destination[intf.tunnel.af] }}
{% endfor %}
```

**Main** (`vyos.j2`) -- sets the source interface, which also controls outer VRF selection:

```jinja
{% for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['gre'] %}
set interfaces tunnel {{ intf.ifname }} source-interface {{ intf.tunnel._source.ifname }}
{% endfor %}
```

The `netsim/extra/tunnel/gre/vyos.initial.j2` template is included in the initial configuration template via the `extra_initial` macro:

```jinja
{% from '_extra_initial.j2' import extra_initial with context %}
{#
    Include interface-related parts of module/plugin configuration, including
    VLANs, VRFs, and tunnels
#}
{{ extra_initial() }}
```

## Test Cases

Integration tests in `tests/integration/tunnel/`:

* `01-gre.yml` -- GRE tunnels over IPv4 and IPv6 transport with OSPFv2/OSPFv3 running over the tunnels. Uses FRR containers to verify OSPF adjacencies, prefix propagation, and end-to-end ping.
* `02-gre-vrf.yml` -- GRE tunnels with VRF transport underlay, verifying that GRE works over a VRF-based transport network.

Coverage tests in `tests/coverage/`:

* `input/gre-source.yml` -- tests automatic tunnel source interface selection with the `tunnel.source.linkid` and `tunnel.source.link.role` options.
* `errors/gre-support.yml` -- tests error conditions: unsupported device, unsupported transport AF, unsupported VRF, and missing tunnel source.
