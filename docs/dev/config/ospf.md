# Configuring OSPF

This document describes the device data model parameters one should consider when creating an OSPF configuration template. For a wider picture, please see [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [Using Ansible Configuration Modules](ospf-ansible-config) section at the bottom of this document.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/ospf/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)
* If you want to support OSPFv2 and OSPFv3, start with the [](ospf-af) section.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(ospf-af)=
## Supporting Multiple Address Families

**ospf.af** variable contains a dictionary of address families configured on the device:

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

*netlab* data model assumes a single OSPF process running in the global routing table. Device-wide parameters are set in **ospf** dictionary:

* **ospf.process** -- OSPF process ID (optional)
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

The device data model assumes that the loopback interface will be placed into the default OSPF area. Use **ospf.area** and **loopback.ipv4** or **loopback.ipv6** attributes to configure OSPF on the loopback interface.

Nexus OS example (**pid** variable was set in the [](#global-ospf-configuration)).

```
interface loopback0
 ip router ospf {{ pid }} area {{ ospf.area }}
!
```

Cisco IOS OSPFv3 example:

```
{% if 'ipv6' in loopback %}
interface Loopback0
 ipv6 ospf {{ pid }} area {{ ospf.area }}
{% endif %}
```

Alternatively, use the **netlab_interfaces** list and configure the loopback interface like any other interface (the OSPF configuration module sets the **ospf.area** parameter on the loopback interface).

## Configuring OSPF Interfaces

OSPF interface parameters are specified within the **ospf** dictionary on individual interfaces. That dictionary may contain these parameters:

* **area** -- interface OSPF area (always present)
* **network_type** -- OSPF network type (optional, use platform default when the value is missing). Allowed values (when specified) are `point-to-point`, `point-to-multipoint`, `broadcast`, `non-broadcast`.
* **passive** -- interface is a passive OSPF interface (optional)
* **cost** -- interface cost
* **bfd** -- BFD is active on the interface (see [](igp-bfd-interaction) and [](igp-bfd-config) for more details).

```{tip}
The **ospf.area‌** parameter is also present on the loopback interface
```

The interface part of the OSPF configuration template starts with a **for** loop over all configured interfaces that have OSPF parameters. You MUST check for presence of **ospf** interface dictionary to exclude external (inter-AS) interfaces from the OSPF routing process.

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

(ospf-ansible-config)=
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
