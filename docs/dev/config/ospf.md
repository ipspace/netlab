(dev-config-ospf)
# Configuring OSPF

This document describes the device data model parameters one should consider when creating an OSPF configuration template. For a wider picture, please see [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [Using Ansible Configuration Modules](dev-ospf-ansible-config) section at the bottom of this document.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/ospf/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)
* If you want to support OSPFv2 and OSPFv3, start with the [](dev-ospf-af) section.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-ospf-features)=
## Device Features

You can use the following device **features.ospf** [device features](dev-device-features) to specify which parts of the OSPF data model your configuration templates implement:

* **unnumbered** -- OSPF runs over unnumbered interfaces
* **default** -- generation of default route
* **import** -- redistribution from other routing protocols
* **timers** -- OSPF timers
* **priority** -- DR election priority
* **password** -- Simple OSPFv2 authentication

(dev-ospf-af)=
## Supporting Multiple Address Families

**ospf.af** variable contains a dictionary of address families configured on the device. The variable is present in global and VRF data structures.

* **ospf.af.ipv4** -- there is at least one interface on which you could run OSPFv2
* **ospf.af.ipv6** -- there is at least one interface on which you could run OSPFv3

OSPFv2 and OSPFv3 are usually configured as separate routing protocols. If your device follows the same paradigm, and if you wish to implement OSPFv2 and OSPFv3:

* Start with a stub template in `netsim/templates/ospf/<nos>.j2`
* Configure OSPFv2 in `netsim/templates/ospf/<nos>.ospfv2.j2`
* Configure OSPFv3 in `netsim/templates/ospf/<nos>.ospfv3.j2`

Use something similar to the following example as the stub template:

```
{% set pid = ospf.process|default(1) %}
{% if ospf.af.ipv4 is defined %}
{% include 'ios.ospfv2.j2' %}
{% endif %}
{% if ospf.af.ipv6 is defined %}
{% include 'ios.ospfv3.j2' %}
{% endif %}
```

## Global OSPF Configuration

*netlab* data model assumes a single OSPF process running in the global routing table (if you need a separate process ID for OSPFv3, add one to the OSPFv2 process ID). Device-wide parameters are set in the node **ospf** dictionary:

* **ospf.process** -- OSPF process ID (optional)

These parameters are set in the node or VRF **ospf** dictionary:

* **ospf.router_id** -- OSPF router ID (always present, should be an IPv4 address)
* **ospf.reference_bandwidth** -- reference bandwidth (optional)
* **ospf.unnumbered** -- OSPF is ran on at least one unnumbered IPV4 interface (optional)
* **ospf.area** -- default OSPF area (always present)

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

## Loopback Configuration

The device data model assumes that the loopback interface will be placed into the default OSPF area, and creates **ospf.area** attribute in the **loopback** interface, making it possible to . iterate over **netlab_interfaces** list (see also [](dev-config-initial)) when configuring OSPF.

However, if you insist on configuring the loopback interface separately, look at the Nexus OS example (**pid** variable was set in the [](#global-ospf-configuration)).

```
interface loopback0
 ip router ospf {{ pid }} area {{ ospf.area }}
!
```

... and the Cisco IOS OSPFv3 example:

```
{% if 'ipv6' in loopback %}
interface Loopback0
 ipv6 ospf {{ pid }} area {{ ospf.area }}
{% endif %}
```

## Configuring OSPF Interfaces

OSPF interface parameters are specified within the **ospf** dictionary on individual interfaces. That dictionary may contain these parameters:

* **area** -- interface OSPF area (always present)
* **network_type** -- OSPF network type (optional, use platform default when the value is missing). Allowed values (when specified) are `point-to-point`, `point-to-multipoint`, `broadcast`, `non-broadcast`.
* **passive** -- interface is a passive OSPF interface (optional)
* **cost** -- interface cost
* **bfd** -- BFD is active on the interface (see [](igp-bfd-interaction) and [](igp-bfd-config) for more details).
* **timers.hello** -- Hello timer
* **timers.dead** -- Dead interval
* **priority** -- DR priority
* **password** -- Simple OSPF authentication password

```{tip}
* The **ospf.area‌** parameter is also present on the loopback interface
* The OSPF timers have to be enabled with the **‌ospf.timers** device feature
* The DR priority is enabled with the **‌ospf.priority** device feature
* The OSPF password is enabled with the **‌ospf.password** device feature
```

The interface part of the OSPF configuration template starts with a **for** loop over all configured interfaces that have OSPF parameters. You MUST check for the presence of the **ospf** interface dictionary to exclude external (inter-AS) interfaces from the OSPF routing process.

You might want to use the interface description as a comment to help you troubleshoot the final configuration snippets:

```
{% for l in interfaces if 'ospf' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
...
{% endfor %}
```

If you want to support OSPFv2 and OSPFv3, you should also check whether IPv4/IPv6 is configured on the interfaces. OSPFv3 example:

```
{% for l in interfaces if 'ospf' in l and 'ipv6' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
...
{% endfor %}
```

The rest of the interface configuration should check the presence of various attributes you decided to support. Nexus OS OSPFv2 example:

```
{% for l in interfaces if 'ospf' in l and 'ipv4' in l %}
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

(dev-ospf-macro)=
## Using Macros for Global- and VRF Configuration

Most devices use a very similar OSPF configuration for the global and the VRF routing processes. It thus makes sense to create that OSPF configuration only once. We're commonly using Jinja2 macros to do that (examples are taken from Arista EOS templates):

1. Define a configuration macro in the **_device_.ospfv2.j2** and **_device_ospfv3.j2** configuration templates:

```
{% macro config(ospf_pid,ospf_vrf,ospf_data,intf_data,bgp={}) %}
```

   The parameters passed to the macro depend on the information you need to configure the OSPF routing process. Arista EOS needs process ID, VRF name, and BGP information (for route redistribution). You should always pass the "global" OSPF parameters and the interface list to the macro.

2. Import macros into the OSPF configuration template:

```
{% import "eos.ospfv2.j2" as ospfv2 %}
{% import "eos.ospfv3.j2" as ospfv3 %}
```

3. Call configuration macros based on OSPF address families running on the box:

```
{% set ospf_pid = ospf.process|default(1) %}
{% if ospf.af.ipv4 is defined %}
{{   ospfv2.config(ospf_pid,False,ospf,netlab_interfaces) }}
{% endif %}
{% if ospf.af.ipv6 is defined %}
{{   ospfv3.config(ospf_pid,False,ospf,netlab_interfaces) }}
{% endif %}
```

   Use **ospf** (node data) and **netlab_interfaces** when configuring global interfaces[^ORV]. Pass the global process ID to the macro and False as the VRF name (if you need these parameters)

4. In the configuration macro, configure global or VRF OSPF process:

```
{% if ospf_vrf %}
router ospf {{ ospf_pid }} vrf {{ ospf_vrf }}
{% else %}
router ospf {{ ospf_pid }}
{% endif %}
```

[^ORV]: The **ospf** parameters are removed from the VRF interfaces in the **interfaces** list, so you don't need to check the VRF membership of individual interfaces.

When using the same configuration macros in the VRF configuration template:

1. Import macros from the OSPF directory:

```
{% import "templates/ospf/eos.ospfv2.j2" as ospfv2 %}
{% import "templates/ospf/eos.ospfv3.j2" as ospfv3 %}
```

2. When iterating over VRFs, check for **ospf** dictionary in VRF data and then call OSPFv2 or OSPFv3 macro based on the **ospf.af** flags.

```
{% for vname,vdata in vrfs.items() if 'ospf' in vdata %}
{%   if vdata.af.ipv4|default(False) %}
{{     ospfv2.config(vdata.vrfidx,vname,vdata.ospf,vdata.ospf.interfaces|default([]),bgp|default({})) }}
{%   endif %}
{%   if vdata.af.ipv6|default(False) %}
{{     ospfv3.config(vdata.vrfidx,vname,vdata.ospf,vdata.ospf.interfaces|default([]),bgp|default({})) }}
{%   endif %}
{% endfor %}
```

   When calling the macro, use the VRF OSPF data (`vdata.ospf`) as the **ospf** parameter, the VRF OSPF interfaces (`vdata.ospf.interfaces`) as the **interfaces** parameter, and the `vdata.vrfidx` (_netlab_'s internal VRF index) as the process ID.

(dev-ospf-ansible-config)=
## Using Ansible Configuration Modules

You might be forced to use Ansible configuration modules instead of generating and deploying a device configuration from a Jinja2 template. In that case, create the list of Ansible tasks needed to configure your device in `netsim/tasks/<nos>/ospf.yml` with **nos** being the value of **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.

Fortinet example (**vdom** variable is set as an Ansible group variable in system settings):

```
---
---
- name: Configure OSPF global settings
  fortinet.fortios.fortios_router_ospf:
    vdom: "{{ vdom }}"
    router_ospf:
      area:
        - id: "{{ ospf.area | ansible.netcommon.ipaddr('address') | default('0.0.0.0') }}"
      auto_cost_ref_bandwidth: "{{ ospf.reference_bandwidth | default(omit) }}"
      router_id: "{{ ospf.router_id }}"

- name: Configure OSPF on loopback
  fortinet.fortios.fortios_router_ospf:
    vdom: "{{ vdom }}"
    router_ospf:
      ospf_interface:
        - name: "loopback0"
          interface: "loopback0"

- name: Configure OSPF on non p2p interfaces
  fortinet.fortios.fortios_router_ospf:
    vdom: "{{ vdom }}"
    router_ospf:
      ospf_interface:
        - name: "{{ interface.ifname }}"
          interface: "{{ interface.ifname }}"
  with_items: "{{ interfaces }}"
  when: interface.type != "p2p" and not (interface.role is defined and interface.role == "external")
  loop_control:
    loop_var: interface

- name: Configure OSPF on p2p interfaces
  fortinet.fortios.fortios_router_ospf:
    vdom: "{{ vdom }}"
    router_ospf:
      ospf_interface:
        - name: "{{ interface.ifname }}"
          interface: "{{ interface.ifname }}"
          network_type: "point-to-point"
  with_items: "{{ interfaces }}"
  when: interface.type == "p2p" and not (interface.role is defined and interface.role == "external")
  loop_control:
    loop_var: interface

... more tasks...
```
