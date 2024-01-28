# Configuring BGP

This document describes the device data model parameters one should consider when creating a BGP device configuration template. For a wider picture, please see the [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [](ospf-ansible-config) for more details.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/bgp/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(bgp-af)=
## Supporting Multiple Address Families

The BGP data model assumes all devices handle dual-stack deployments and providers **bgp.ipv4** and **bgp.ipv6** attributes to indicate which address families you should configure.

BGP neighbors data can contain **ipv4** and **ipv6** addresses. If a neighbor has both addresses you have to configure two BGP neighbor sessions, one for IPv4, the other one for IPv6.

_netlab_ assumes the IPv4 BGP session carries the IPv4 address family (plus other address families like MPLS/VPN or EVPN) and the IPv6 BGP session carries the IPv6 address family. It's possible to disable the default address family with the **activate** BGP neighbor attribute.

## Global BGP Parameters

*netlab* data model assumes a single BGP process running in the global routing table and VRFs (VRFs are not covered in this document). Device-wide parameters are set in **bgp** dictionary:

* **bgp.advertise_loopback** (boolean) -- When set to *True*, the BGP process should advertise the IPv4/IPv6 prefix assigned to loopback interface
* **bgp.as** -- The BGP AS number (always present)
* **bgp.community** -- The BGP communities propagation rules
* **bgp.ipv4** -- You should configure IPv4 BGP address family
* **bgp.ipv6** -- You should configure IPv6 BGP address family
* **bgp.neighbors** -- A list of IBGP and EBGP neighbors
* **bgp.next_hop_self** -- When set to *True*, the BGP process should set itself as the next hop on EBGP routes propagated as IBGP routes.
* **bgp.originate** -- A list of additional IPv4 prefixes that should be advertised by the BGP process. You'll probably have to create static routes to support these prefixes.
* **bgp.router_id** -- The BGP router ID
* **bgp.rr** -- When set to *True*, the device is a BGP route reflector.

## Interface BGP Parameters

There's a single BGP-related interface parameter:

* **bgp.advertise** -- advertise the prefix assigned to the interface in the BGP process. Used to advertise stub networks instead of doing redistribution of connected prefixes.

## BGP Neighbors

Each entry in the **bgp.neighbors** list describes an adjacent device that could be an endpoint of IBGP or EBGP sessions. A single adjacent device might have an IPv4 and an IPv6 BGP session, which would usually have to be configured as two distinct BGP neighbors.

A description of a BGP neighbor might have these parameters:

* **activate.ipv4** -- Activate the IPv4 AF on the IPv4 BGP session.
* **activate.ipv6** -- Activate the IPv6 AF on the IPv6 BGP session.
* **as** -- Remote autonomous system
* **local_as** -- Local autonomous system (when using **local-as** functionality)
* **ipv4** -- IPv4 address of an IPv4 BGP neighbor
* **ipv6** -- IPv6 address of an IPv6 BGP neighbor
* **name** -- Neighbor name (used in descriptions)
* **type** -- Neighbor type: **ibgp**, **ebgp** or **localas_ibgp**. The **localas_ibgp** type is used when the **local_as** turns an EBGP session into a fake IBGP session.

## BGP Configuration Framework

The global BGP configuration should configure the BGP process and the address families. The configuration template should then use the **bgp.neighbors** list to configure individual BGP sessions, and activate those sessions within the address families. Finally, the template should originate the local prefixes.


Cisco IOS OSPFv2 example:

```
{% set pid = ospf.process|default(1) %}
router ospf {{ pid }}
{% if ospf.router_id|ipv4 %}
 router-id {{ ospf.router_id }}
{% endif %}
{% if ospf.reference_bandwidth is defined %}
 auto-cost reference-bandwidth {{ ospf.reference_bandwidth }}
{% endif %}
```

Arista EOS OSPFv3 example:

```
{% set pid = ospf.process|default(1) %}
ipv6 router ospf {{ pid }}
 router-id {{ ospf.router_id }}
{% if ospf.reference_bandwidth is defined %}
 auto-cost reference-bandwidth {{ ospf.reference_bandwidth }}
{% endif %}
```

## Configuring OSPF Interfaces

OSPF interface parameters are specified within the **ospf** dictionary on individual interfaces. That dictionary may contain these parameters:

* **area** -- interface OSPF area (always present)
* **network_type** -- OSPF network type (optional, use platform default when the value is missing). Allowed values (when specified) are `point-to-point`, `point-to-multipoint`, `broadcast`, `non-broadcast`.
* **passive** -- interface is a passive OSPF interface (optional)
* **cost** -- interface cost
* **bfd** -- BFD is active on the interface (see [](igp-bfd-interaction) and [](igp-bfd-config) for more details).

Interface part of OSPF configuration template starts with a **for** loop over all configured interfaces that have OSPF parameters. You MUST check for presence of **ospf** interface dictionary to exclude external (inter-AS) interfaces from the OSPF routing process.

You might want to use interface description as a comment to help you troubleshoot the final configuration snippets:

```
{% for l in interfaces if 'ospf' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
...
{% endfor %}
```

If you want to support OSPFv2 and OSPFv3 you should also check whether IPv4/IPv6 is configured on the interfaces. OSPFv3 example:

```
{% for l in interfaces if 'ospf' in l and 'ipv6' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
...
{% endfor %}
```

The rest of the interface configuration should check the presence of various attributes you decided to support. Nexus OS OSPFv2-only example:

```
{% for l in interfaces if 'ospf' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
 ip router ospf {{ pid }} area {{ l.ospf.area }}
{%   if l.ospf.network_type|default("") in ["broadcast","point-to-point"] %}
 ip ospf network {{ l.ospf.network_type }}
{%   endif %}
{%   if l.ospf.cost is defined %}
 ip ospf cost {{ l.ospf.cost }}
{%   endif %}
{%   if l.ospf.passive|default(False) %}
 ip ospf passive-interface
{%   endif %}
{%   if l.ospf.bfd|default(False) %}
 ip ospf bfd
{%   endif %}
!
{% endfor %}
```

### Configuring Passive Interfaces

Some network devices configure passive interfaces within the routing protocol configuration (example: Cisco IOS, Arista EOS), others configure them within interface configuration (see Nexus OS example above).

Cisco IOS passive interface configuration is done within **router ospf** block. OSPFv2 example:

```
{% set pid = ospf.process|default(1) %}
router ospf {{ pid }}
{% if ospf.router_id|ipv4 %}
 router-id {{ ospf.router_id }}
{% endif %}
{% if ospf.reference_bandwidth is defined %}
 auto-cost reference-bandwidth {{ ospf.reference_bandwidth }}
{% endif %}
{% for l in interfaces if l.ospf.passive|default(False) %}
 passive-interface {{ l.ifname }}
{% endfor %}
```

### Limited Network Type Support

Some devices (example: Nexus OS) don't support all OSPF network types. OSPF module checks the validity of **network_type** value, but not the device support -- check **ospf.network_type** value in configuration templates to prevent deployment errors.

Please note that the **ospf.network_type** is an optional attribute and might not be present. Use `l.ospf.network_type is defined` or `l.ospf.network_type|default("")` in your template.

Nexus OS OSPFv2-only example:

```
{% for l in interfaces if 'ospf' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
{%   if l.ospf.network_type|default("") in ["broadcast","point-to-point"] %}
 ip ospf network {{ l.ospf.network_type }}
{%   endif %}
!
{% endfor %}
```

### Mapping Network Type into Device-Specific Keywords

Junos configures OSPF network types with different keywords than most other devices, and uses lack of **interface-type** parameter to indicate *broadcast* OSPF network. 

If you're facing a similar challenge, use a mapping dictionary in your template:

```
{% set KW_NETWORK_TYPE = {'point-to-point': 'p2p','point-to-multipoint': 'p2mp', 'non-broadcast': 'nbma' } %}
protocols {
  ospf {
{% for l in interfaces if 'ospf' in l %}
    area {{ l.ospf.area }} {
      interface {{ l.ifname }} {
{%   if l.ospf.network_type is defined and l.ospf.network_type != 'broadcast' %}
        interface-type {{ KW_NETWORK_TYPE[l.ospf.network_type] }};
{%   endif %}
```

### Unnumbered IPv4 Interfaces

Arista EOS needs additional OSPF settings to support OSPF over unnumbered IPv4 interfaces. Use **ospf.unnumbered** parameter to detect OSPF running over IPv4 unnumbered interface. Arista EOS OSPFv2 example:

```
router ospf {{ pid }}
{% if ospf.router_id|ipv4 %}
 router-id {{ ospf.router_id }}
{% endif %}
{% if ospf.unnumbered is defined %}
 interface unnumbered hello mask tx 0.0.0.0
{% endif %}
```
