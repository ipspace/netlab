(dev-config-services)=
# Configuring Network Services

This document describes the device data model parameters one should consider when creating a network services configuration template. For a wider picture, please see [](dev-device-features) or [](../devices.md).

The services module currently supports two client-server services: **DNS** (fully implemented) and **syslog** (attribute schema defined, transformation logic ready, configuration templates not yet implemented).

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/ansible/templates/services/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details).
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in svc_data` in your Jinja2 templates to check for the presence of optional attributes.
* The `services` module runs after the `vrf` module during the topology transformation phase. All VRF information is therefore available when services are being processed.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Module Attributes

The services module is defined in `netsim/modules/services.yml`. The attribute schema supports two services (`dns` and `syslog`) at both the **global** topology level and the **node** level. Each service can define a **server** list (node names), direct **ipv4**/**ipv6** addresses, a **transport_vrf**, and a **domain** (DNS only).

The **server** sub-attribute within the node-level attributes defines what happens when a node acts as a service provider:

* `services.server.dns` -- a dictionary that may contain **forwarder** addresses (`ipv4`/`ipv6` lists). The attribute can also be set to `True` (boolean) as a shorthand.
* `services.server.syslog` -- a boolean flag indicating the node is a syslog server.

The services module transformation (implemented in `netsim/modules/services.py`, class `Services`, method `module_post_transform`) runs during the `post_transform` phase. For every node that has a `services` attribute, it performs these steps:
### Server Resolution (`resolve_servers`)

For each service key present on a node (e.g., `dns`):

1. If the node has neither `services.<kw>.server` nor `services.<kw>.ipv4`/`ipv6`, the module reports a `MissingValue` error -- every node using a service must specify how to reach it.

2. If `services.<kw>.server` lists node names, the module resolves each server name into IP addresses:

   * It looks up the server node in the topology.
   * It verifies the server node has `services.server.<kw>` configured. If not, the error is recorded and reported later.
   * It finds the server's control-plane endpoint using `_routing.get_remote_cp_endpoint()`, which returns the loopback interface (for routers) or the best available physical interface.
   * It matches the client's address families (`node.af`) against the server endpoint's addresses and populates `services.<kw>.ipv4` and `services.<kw>.ipv6` lists on the client node with the server's control-plane IP addresses.

3. If no address family match is found between client and server, an error is recorded.

### Helper Fields (`set_dns_fields`)

After server resolution, the DNS-specific helper fields are set:

* `services.dns._server_list` -- combined list of all IPv6 followed by IPv4 DNS server addresses, created to simplify template logic.
* `services.dns._no_hosts` -- set to `True` when the node is a DNS client but **not** a DNS server. This flag is used in initial configuration templates to suppress `ip host` entries (which are unnecessary when the node has explicit DNS servers).

### Container-Specific Handling (`disable_shared_hosts`)

For containerlab nodes that use DNS services (client or server), any `:shared` suffix is removed from `clab.config_templates.hosts`. DNS-enabled containers must have their own `/etc/hosts` file (not the shared one) because DNS resolution should take precedence over static host entries.

### Feature and VRF Validation

* `check_feature_support` -- validates that the device supports the requested services features (both client and server roles), using blacklist mode.
* `check_vrf` -- validates that `transport_vrf` values (if specified) match existing VRFs on the node.
* `print_client_server_errors` -- reports any resolution failures (node not a server, no common address family).

## Node Data Attributes

### Client Attributes

After transformation, a DNS client node has these attributes in `services.dns`:

* **server** (list of node names, original input) -- nodes that act as DNS servers for this client. Resolved into `ipv4`/`ipv6` lists during transformation.
* **ipv4** (list of IPv4 addresses) -- IPv4 addresses of DNS servers, populated by the transformation process or set directly by the user.
* **ipv6** (list of IPv6 addresses) -- IPv6 addresses of DNS servers.
* **domain** (string, optional) -- DNS domain search suffix.
* **transport_vrf** (string, optional) -- VRF used to reach DNS servers.
* **\_server_list** (list of IP addresses) -- combined IPv6+IPv4 server addresses, generated by `set_dns_fields()`. This is the primary field used in configuration templates.
* **\_no_hosts** (boolean, optional) -- set to `True` when the node is a pure DNS client (not a server). Suppresses static `ip host` entries in the initial config.

Syslog client attributes follow the same schema (`server`, `ipv4`, `ipv6`, `transport_vrf`) but without `domain` and the helper fields.

### Server Attributes

A node acting as a DNS server has these attributes in `services.server`:

* **dns** -- either `True` (boolean) or a dictionary with optional **forwarder**:
  * `forwarder.ipv4` (list of IPv4 addresses) -- upstream DNS forwarders
  * `forwarder.ipv6` (list of IPv6 addresses) -- upstream DNS forwarders

A node acting as a syslog server sets `services.server.syslog` to `True`.

## Device Features

Device support for services is declared in the device YAML files under `features.services`. The following capabilities can be advertised:

* **dns** (boolean or dictionary) -- the device supports DNS client configuration. When set to a dictionary, it may contain `transport_vrf: False` to indicate the device does not support VRF-aware DNS.
* **syslog** (boolean) -- the device supports syslog client configuration.
* **server.dns** (boolean) -- the device can act as a DNS server.
* **server.syslog** (boolean) -- the device can act as a syslog server.

Examples from existing device definitions:

```yaml
# Arista EOS -- full DNS client support
features:
  services:
    dns: True

# FRR -- DNS client without VRF support
features:
  services:
    dns:
      transport_vrf: False

# "none" device -- full support for both services and server roles
features:
  services:
    dns: True
    syslog: True

# dnsmasq daemon -- DNS server (dnsmasq.yml)
features:
  services:
    dns: true
    server.dns: true
```

## Configuration Templates

### DNS Client Templates

The DNS client configuration template (`netsim/ansible/templates/services/<nos>.j2`) should use `services.dns._server_list` to obtain the combined list of DNS server addresses, potentially limited by the device's supported number of DNS servers.

Arista EOS template (`netsim/ansible/templates/services/eos.j2`) (supports DNS-in-VRF, up to six DNS servers):

```jinja
{% if services.dns._server_list is defined %}
ip name-server {% if services.dns.transport_vrf is defined
  %}vrf {{ services.dns.transport_vrf }} {% endif
  %}{{ services.dns._server_list[:6]|join(' ') }}
{% endif %}
{% if services.dns.domain|default(False) %}
ip domain-list {{ services.dns.domain }}
{% endif %}
```

Linux/FRR template (`netsim/ansible/templates/services/frr.j2`) generates a shell script that writes `/etc/resolv.conf` using the same Linux resolv.conf snippet used in the initial configuration:

```jinja
{% if clab is not defined %}
{%   if services.dns._server_list is defined %}
cat <<'CONFIG' >/etc/resolv.conf
{%     include 'initial/linux/resolv.j2' +%}
CONFIG
{%   endif %}
{% endif %}
```

The shared Linux resolver template (`netsim/ansible/templates/initial/linux/resolv.j2`) renders `nameserver` lines for the first three DNS servers (preferring IPv6 over IPv4), with a fallback to the Docker DNS server (`127.0.0.11`), and optionally sets the `search` domain:

```jinja
{% for srv_ip in (services.dns._server_list|default(['127.0.0.11']))[:3] %}
nameserver {{ srv_ip }}
{% endfor %}
{% if services.dns.domain|default(False) %}
search {{ services.dns.domain }}
{% endif %}
options edns0 trust-ad ndots:0
```

**Note:** Linux containers always receive the resolv.conf snippet mapped to the container. VM-based devices (FRR) only generate it when DNS servers are explicitly defined.

### Initial Configuration Integration

Device initial configuration templates should check the `services.dns._no_hosts` flag to decide whether to generate static `ip host` entries. When the node is a DNS client but not a DNS server, the `_no_hosts` flag is set, and the static host entries are suppressed (the node will use DNS instead).

```jinja
{% if services.dns._no_hosts is not defined %}
{%   for hname,hdata in hosts.items() if 'ipv4' in hdata and hname != inventory_hostname %}
ip host {{ hname|replace('_','') }} {{ hdata.ipv4|join (' ') }}
{%   endfor %}
{% endif %}
```

## Test Cases

The relevant integration test cases are in `tests/integration/services/` directory:

* `01-dns-client.yml` -- end-to-end DNS client test using a `dnsmasq` server. Verifies name resolution (ping by hostname) and DNS query logging on the server.

Coverage tests in `tests/coverage/`:

* `input/svc-server.yml` -- tests DNS server name-to-address resolution and the `_no_hosts` flag behavior.
* `errors/svc-errors.yml` -- tests error conditions: missing VRF, unsupported features, no common address family, and referencing a non-server node as a service provider.
