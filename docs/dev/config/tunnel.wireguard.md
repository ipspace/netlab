(dev-config-tunnel-wireguard)=
# Configuring WireGuard Tunnels

This document describes the device data model parameters one should consider when creating a WireGuard tunnel configuration template. WireGuard tunnels are implemented as a plugin (`tunnel.wireguard`) that reuses the shared point-to-point tunnel utilities from `netsim/extra/tunnel/_p2p.py`.

The plugin supports WireGuard encrypted tunnels as point-to-point links between exactly two nodes, with IPv4 or IPv6 transport encapsulation, automatic key generation, and unique UDP listen port allocation.

**Notes:**

* The configuration template (in Jinja2 format) should be stored in `netsim/extra/tunnel/wireguard/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable.
* Some devices require an initial configuration template to create the WireGuard interface before other modules can reference it. Those templates are stored as `<nos>.initial.j2` and are executed during the initial configuration phase.
* To use WireGuard tunnels, add `plugin: [ tunnel.wireguard ]` to the lab topology.
* The `wireguard-tools` package must be available on Linux nodes (the plugin installs it automatically via `netlab_linux_packages`).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Data Model

WireGuard tunnel attributes are defined in `netsim/extra/tunnel/wireguard/defaults.yml` within the `attributes.link.tunnel` namespace. Every link with `tunnel.mode: wireguard` becomes a WireGuard tunnel link.

### Link-Level Attributes (per tunnel)

* **tunnel.mode** (required) -- must be set to `wireguard`.
* **tunnel.af** (optional, string) -- transport address family. Valid values: `ipv4`, `ipv6`. When not set, auto-derived from the selected source interface (preferring IPv4).
* **tunnel.vrf** (optional, string) -- transport VRF name. When set, the tunnel operates over a VRF; Linux nodes configure policy routing and `udp_l3mdev_accept` to make this work.
* **tunnel.private_key** (optional, string) -- WireGuard private key (base64). Auto-generated when omitted.
* **tunnel.public_key** (optional, string) -- WireGuard public key (base64). Derived from `private_key` if only the private key is provided, or auto-generated alongside the private key.
* **tunnel.listen_port** (optional, integer) -- UDP port for incoming WireGuard connections. Must be unique per tunnel per node. Auto-allocated starting from 51820 when not specified. Range: 1--65535.
* **tunnel.allowed_ips** (optional, string) -- comma-separated IP prefixes allowed for the remote peer. Defaults to `0.0.0.0/0` (plus `::/0` for dual-stack nodes).
* **tunnel.persistent_keepalive** (optional, integer) -- keepalive interval in seconds. Defaults to 25. Set to 0 to disable.
* **tunnel.source** (optional, dictionary) -- controls how the tunnel source interface is selected. Same filtering logic as GRE tunnels (see [](dev-config-tunnel-gre)).

### Transformed Attributes (set by the plugin)

After transformation, each WireGuard tunnel interface receives:

* **tunnel.\_source** -- resolved underlay source data:
  * `ifname` (string) -- name of the selected source interface.
  * `ipv4` or `ipv6` (string) -- source IP address for the transport AF.
  * `mtu` (integer) -- MTU of the source interface.
  * `public_key` (string) -- node's WireGuard public key for this tunnel.
  * `listen_port` (integer) -- allocated UDP listen port.
* **tunnel.\_destination** -- peer endpoint data (copied from neighbor's `tunnel._source`):
  * `ipv4` or `ipv6` (string) -- peer's source IP address.
  * `mtu` (integer) -- peer's source MTU.
  * `public_key` (string) -- peer's WireGuard public key.
  * `listen_port` (integer) -- peer's UDP listen port.
* **tunnel.allowed_ips** (string) -- defaults to `0.0.0.0/0` (IPv4) or plus `::/0` (dual-stack).
* **mtu** (integer) -- calculated from underlay MTU minus WireGuard overhead (80 bytes for IPv6 underlay, 60 for IPv4).

The interface also gets:

* **type** set to `tunnel` during `pre_transform`.
* **virtual_interface** set to `True` during link transformation.
* Interface description enhanced with `[WireGuard tunnel]` during `post_transform`.

## Device Features

Device support for WireGuard tunnels is declared under `features.tunnel.wireguard`. The only configurable option is VRF support, for example (FRR):

```yaml
features:
  tunnel:
    wireguard: [ vrf ]
```

Unlike GRE, WireGuard does not use the transport AF feature check (`t_af=False` in `feature_check`). Address family selection is handled internally by the plugin's `wireguard_intf_defaults()` function, which derives the AF from the source interface.

## WireGuard Key Management

The plugin provides comprehensive key management in `ensure_tunnel_keys()`, supporting three modes:

1. **User supplies both keys** -- `tunnel.private_key` and `tunnel.public_key` are both present. No derivation needed.
2. **User supplies only private key** -- `tunnel.private_key` is present without `tunnel.public_key`. The public key is derived by shelling out to `wg pubkey`.
3. **No keys supplied** -- both keys are auto-generated via `wg genkey` and `wg pubkey`.

A `public_key` without a corresponding `private_key` is rejected as an error (it is impossible to derive a private key from a public key).

Key generation and derivation require the `wireguard-tools` package. If it is not installed, a fatal error directs the user to install it or supply explicit keys. In verbose mode, key generation events are logged.

## Port Allocation

Every WireGuard tunnel on a node needs a unique UDP listen port (Linux cannot bind multiple WireGuard sockets to the same port). The `allocate_listen_ports()` function handles this:

* User-specified `tunnel.listen_port` values are preserved.
* Unspecified ports are auto-allocated starting from the `_start` value (51820), increasing by one for each additional tunnel.
* Duplicate user-specified ports on the same node are reported as errors.

The allocation uses the `_dataplane` module's ID set mechanism (`create_id_set`, `extend_id_set`, `set_id_counter`, `get_next_id`) to guarantee collision-free assignment within the range 51820--65535.

## Transformation Process

The plugin hooks into the topology transformation pipeline via two hooks in `netsim/extra/tunnel/wireguard/__init__.py`:

### pre_transform

1. **`_tunnel.set_tunnel_type(topology)`** -- marks all links with `tunnel.mode: wireguard` as `type: tunnel`.
2. **Validates P2P topology** -- every WireGuard tunnel link must have exactly two nodes.

### post_transform

1. **`_p2p.feature_check(topology, t_mode='wireguard')`** -- validates device support for WireGuard tunnels. Calls `api.node_config(ndata, 'tunnel.wireguard')` for each node that passes.
2. **`_p2p.tunnel_source(topology, node_iflist)`** -- resolves underlay source interfaces and populates `tunnel._source.ifname`, `tunnel._source.ipv4`/`ipv6`, and `tunnel._source.mtu`.
3. **`allocate_listen_ports(ndata, topology)`** -- assigns unique UDP listen ports per tunnel.
4. **`add_linux_packages(ndata, topology)`** -- ensures `wireguard-tools` is installed on Linux-based nodes.
5. **`wireguard_intf_defaults(ndata, intf, topology)`** -- sets per-interface defaults:
   * Ensures key material exists (generates or derives as needed).
   * Auto-derives `tunnel.af` from the source interface.
   * Sets `tunnel.allowed_ips` to `0.0.0.0/0` (plus `::/0` for dual-stack).
   * Calculates tunnel MTU from underlay MTU minus overhead (80 for IPv6, 60 for IPv4).
   * Copies `public_key` and `listen_port` into `tunnel._source` for peer discovery.
6. **`_p2p.tunnel_destination(topology, node_iflist)`** -- copies each neighbor's `tunnel._source` (including `ipv4`/`ipv6`, `public_key`, `listen_port`) into the local `tunnel._destination`.

## Configuration Templates

### FRR / Linux

Generates a bash script that creates the WireGuard interface, configures VRF underlay routing policy, and sets the WireGuard configuration with `wg set`:

```bash
{% for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['wireguard'] %}
if [ ! -e /sys/class/net/{{ intf.ifname }} ]; then
  ip link add {{ intf.ifname }} type wireguard
fi
{{ linux_intf_sysctl(intf,role,activate=False) }}

{%   set vrf_name = intf.tunnel.vrf|default('') %}
{%   if vrf_name %}
{%     set rule_pref = 10000 + intf.ifindex %}
setup_wg_vrf_underlay {{ vrfs[vrf_name].vrfidx }} {{ rule_pref }} {{ intf.tunnel.af }}
{%   endif %}

{%   set dst = intf.tunnel._destination %}
{%   set peer_ip = ('[' ~ dst.ipv6 ~ ']') if intf.tunnel.af == 'ipv6' else dst.ipv4 %}
{%   set peer_endpoint = peer_ip ~ ':' ~ dst.listen_port %}
wg set {{ intf.ifname }} \
  private-key <(printf '%s\n' '{{ intf.tunnel.private_key }}') \
  listen-port {{ intf.tunnel.listen_port }} \
{%   if vrf_name %}  fwmark {{ rule_pref }} \{% endif -%}
  peer {{ dst.public_key }} \
  allowed-ips {{ intf.tunnel.allowed_ips }} \
  endpoint {{ peer_endpoint }} \
  persistent-keepalive {{ intf.tunnel.persistent_keepalive }}

ip link set dev {{ intf.ifname }} up
{% endfor %}
```

Key details:

* The private key is passed via `<(printf '%s\n' '<key>')` (process substitution) to avoid exposing it on the command line.
* IPv6 peer endpoints are wrapped in brackets (`[::1]:51820`), matching the RFC 3986 URI syntax required by `wg set`.
* VRF underlay uses a shell function `setup_wg_vrf_underlay` that enables `net.ipv4.udp_l3mdev_accept=1` (required for the WireGuard socket to receive packets from VRF interfaces) and adds a policy routing rule matching the tunnel's `fwmark`.

### RouterOS 7

Requires two templates:

**Initial** (`routeros7.initial.j2`) -- creates the WireGuard interface:

```jinja
{% for l in interfaces if l.type == 'tunnel' and l.tunnel.mode == 'wireguard' %}
{%   set vrf_str = 'vrf=' + l.tunnel.vrf if l.tunnel.vrf|default('') else '' %}
/interface/wireguard add name={{ l.ifname }} listen-port={{ l.tunnel.listen_port }} {{ vrf_str }} private-key="{{ l.tunnel.private_key }}"
{% endfor %}
```

**Main** (`routeros7.j2`) -- adds WireGuard peers:

```jinja
{% for intf in netlab_interfaces if intf.tunnel.mode|default('') in ['wireguard'] %}
{%   set dst = intf.tunnel._destination %}
{%   set peer_ip = ('[' ~ dst.ipv6 ~ ']') if intf.tunnel.af == 'ipv6' else dst.ipv4 %}
{%   set peer_endpoint = peer_ip ~ ':' ~ dst.listen_port %}
/interface/wireguard/peers add interface={{ intf.ifname }} public-key="{{ dst.public_key }}" allowed-address={{ intf.tunnel.allowed_ips }} endpoint-address={{ peer_ip }} endpoint-port={{ dst.listen_port }} persistent-keepalive={{ intf.tunnel.persistent_keepalive }}
{% endfor %}
```

The `netsim/extra/tunnel/wireguard/routeros7.initial.j2` template is included in the initial configuration template via the `extra_initial` macro:

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

* `11-wireguard.yml` -- dual-stack WireGuard tunnels with OSPFv2/OSPFv3. Tests IPv4 and IPv6 connectivity, prefix propagation, full MTU packets (1500 bytes), and end-to-end connectivity between remote peers.
* `12-wireguard-vrf.yml` -- WireGuard tunnels in a transport VRF. Verifies OSPF adjacencies, prefix propagation, ping, and MTU when the underlay is VRF-isolated.

Coverage tests in `tests/coverage/`:

* `input/wg-unique-ports.yml` -- regression test for issue #3706. Verifies that multiple WireGuard tunnels on the same node get unique UDP listen ports (51820, 51821, ...).
* `input/wg-listen-port.yml` -- regression test for issue #3703. Verifies that a user-specified `tunnel.listen_port` is preserved on both peers and not overwritten by the auto-allocation logic.
