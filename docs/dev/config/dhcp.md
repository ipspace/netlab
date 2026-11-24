(dev-config-dhcp)=
# Configuring DHCP Clients, Servers, and Relays

This document describes the device data model parameters used in DHCP device configuration templates. Please see the [contributing new devices](dev-new-devices) document for a wider picture.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/ansible/templates/dhcp/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](dev-devices-ansible-vars) for more details).
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)`, or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-dhcp-features)=
## Device Features

You can use the following **features.dhcp** [device features](dev-device-features) to specify which DHCP features your configuration template implements:

* **client.ipv4** -- The template configures IPv4 DHCP clients. The **dhcp** module reports an error when a device without this feature uses an IPv4 DHCP client.
* **client.ipv6** -- The template configures DHCPv6 clients (same check as for **client.ipv4**)
* **client.routing** -- The device can run OSPF or IS-IS over DHCP client interfaces. The **dhcp** module reports an error when a device without this feature runs a routing protocol over a DHCP client interface.
* **client.default** -- The template implements the **dhcp.client.default** interface attribute (accepting or refusing the IPv4 default route received from the DHCP server). This feature is not checked by the **dhcp** module; it is used only in the [supported features tables](dev-features-tables).
* **relay** -- The template configures DHCP relaying. Set it to **true** if the template configures IPv4 and IPv6 relays, or to a dictionary of supported address families (for example, `relay.ipv4: true`). The **dhcp** module reports an error when a device that does not support DHCP relaying (for the specified address family) is used as a DHCP relay.
* **vrf** -- The template configures inter-VRF DHCP relaying. The **dhcp** module reports an error when a device without this feature performs inter-VRF DHCP relaying.
* **server** -- The device can be a DHCP server (IPv4 and IPv6). The **dhcp** module reports an error when a device without this feature has the **dhcp.server** node attribute set.
* **server_vrf** -- The template configures VRF-aware DHCP pools. This feature is not checked by the **dhcp** module; it is used only in the [supported features tables](dev-features-tables).
* **caveats.client**, **caveats.relay**, **caveats.vrf** -- The anchor of the [caveats](platform-caveats) section describing the limitations of DHCP clients, DHCP relays, or inter-VRF DHCP relays (used only to add caveat links to the [supported features tables](dev-features-tables))

(dev-dhcp-node)=
## Node Parameters

The **dhcp** module sets these parameters in the node **dhcp** dictionary:

* **server** (bool) -- The node is a DHCP server
* **pools** (list) -- The DHCP pools the server should configure (present only on DHCP servers, see [](dev-dhcp-pools))
* **relay** (bool) -- The node has at least one interface running a DHCP relay
* **vrf** (bool) -- The DHCP relay should insert the RFC 6607 VPN options into the relayed DHCP requests, or the DHCP server should use VRF-aware DHCP pools. The **dhcp** module sets this parameter on DHCP relays performing inter-VRF relaying and on DHCP servers with pools in VRF subnets unless the user sets it to **false**.

Typical template code that enables the RFC 6607 options looks like this (Arista EOS):

```jinja
{% if dhcp.vrf|default(False) %}
ip dhcp relay information option
!
{% endif %}
```

(dev-dhcp-pools)=
### DHCP Pools

The **dhcp** module builds the DHCP pools from the subnets (links or VLANs) with at least one DHCP client and copies them into the **dhcp.pools** list of every DHCP server. Each pool has these attributes:

* **name** -- The link name, or `vlan_<vlan-name>` (converted into an identifier) for VLAN subnets
* **clean_name** -- The pool name that can be used as an identifier in device configurations
* **ipv4** and **ipv6** -- The IPv4/IPv6 subnet prefix (optional)
* **gateway.ipv4** and **gateway.ipv6** -- The default gateway IPv4/IPv6 address (optional)
* **excluded.ipv4** and **excluded.ipv6** -- The lists of statically assigned IPv4/IPv6 addresses (optional)
* **vrf** -- The subnet VRF (optional). Use it only when **dhcp.vrf** is set.

This is the Cisco IOS DHCP server template (simplified):

```jinja
{% for pool in dhcp.pools|default([]) if 'ipv4' in pool %}
ip dhcp pool {{ pool.clean_name }}
{%   if pool.vrf is defined and dhcp.vrf|default(False) %}
 vrf {{ pool.vrf }}
{%   endif %}
 network {{ pool.ipv4.split('/')[0] }} {{ pool.ipv4|ansible.utils.ipaddr('netmask') }}
{%   if pool.gateway.ipv4 is defined %}
 default-router {{ pool.gateway.ipv4 }}
{%   endif %}
{% endfor %}
```

(dev-dhcp-interface)=
## Interface Parameters

The **dhcp** module sets these parameters in the interface **dhcp** dictionary (VLAN interfaces are in the same **interfaces** list as physical interfaces):

* **client.ipv4** and **client.ipv6** (bool) -- Run an IPv4/IPv6 DHCP client on the interface. The **dhcp** module removes the static IPv4/IPv6 address from DHCP client interfaces.
* **client.default** (bool) -- Accept (or refuse) the IPv4 default route from the DHCP server. The parameter is set only when specified by the user; by default, the default route is accepted.
* **server** (list) -- Run a DHCP relay on the interface; the list contains the names of the DHCP servers.
* **relay.ipv4** and **relay.ipv6** (list) -- The IPv4/IPv6 addresses of the DHCP servers. Use these lists, not the **server** list, to configure DHCP relays. An address family is present only when there are DHCP clients using that address family on the interface subnet.
* **vrf** (string) -- Relay DHCP requests to DHCP servers in the specified VRF. The value **global** means "global routing table".

For example, this is the interface part of the Arista EOS DHCP template:

```jinja
{% for intf in interfaces if intf.dhcp is defined %}
interface {{ intf.ifname }}
{%   if intf.dhcp.client.ipv4 is defined %}
{%     if intf.dhcp.client.default|default(True) is sameas true %}
  dhcp client accept default-route
{%     endif %}
  ip address dhcp
{%   endif %}
{%   for target in intf.dhcp.relay.ipv4|default([]) %}
{%     set vrf = intf.dhcp.vrf|default('') %}
{%     set vrf_kw = ' vrf ' + ('default' if vrf == 'global' else vrf) if vrf else '' %}
  ip helper-address {{ target }}{{ vrf_kw }}
{%   endfor %}
{%   for target in intf.dhcp.relay.ipv6|default([]) %}
  ipv6 dhcp relay destination {{ target }}
{%   endfor %}
{% endfor %}
```

```{tip}
Some devices must start the DHCP client during initial device configuration (for example, before routing protocols are configured). Put that configuration in the `netsim/ansible/templates/dhcp/<nos>.initial.j2` template and include it in the initial device configuration with the `extra_module_initial(['dhcp'])` macro (see the Cisco IOS initial configuration template for an example).
```

## Integration Tests

The DHCP integration tests are in the `tests/integration/dhcp` directory:

* `01-ipv4-client.yml` and `02-ipv6-client.yml` -- IPv4/IPv6 DHCP clients
* `03-ipv4-server.yml` and `04-ipv6-server.yml` -- IPv4/IPv6 DHCP servers
* `11-ipv4-relay.yml` and `12-ipv6-relay.yml` -- IPv4/IPv6 DHCP relays
* `21-ipv4-relay-vrf-global.yml` -- Inter-VRF IPv4 DHCP relay
* `31-ipv4-client-ospf.yml` and `32-ipv6-client-ospf.yml` -- OSPF running over DHCP client interfaces
