(dev-config-initial)=
# Initial Device Configuration

This document describes the device data model parameters to consider when creating an initial device configuration template. Please see the [contributing new devices](../devices.md) document for a broader picture.

Most of the document assumes you have already created an Ansible task list that can deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see the [Using Ansible Configuration Modules](initial-ansible-config) section at the bottom of this document.

The device configuration template (in Jinja2 format) should be stored in `netsim/templates/initial/<nos>.j2` with **nos** being the value of **netlab_device_type** or  **ansible_network_os** Ansible variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Static Configuration

Your device template should start with the static configuration needed to make your device usable. You can configure all relevant parameters in the initial device configuration or include the relevant configuration snippets in the box-building instructions.

For example, the Cisco IOS configuration template enables LLDP, turns off DNS lookup, and removes banners:

```
no ip domain lookup
!
lldp run
!
no banner exec
no banner login
no banner incoming
```

## System Configuration

Use the following variables to set global configuration parameters:

* **inventory_hostname** -- device name. You might need to remove special characters (most likely underscores) from the device name.
* **af.ipv4** and **af.ipv6** are flags indicating whether IPv4 or IPv6 is enabled on this device. If the address family is not active on the device, the flags are missing, and the only value you'll ever see is **True**.
* **mtu** -- system-wide MTU (when supported by the device, otherwise you'll get **mtu** setting on individual interfaces)
* **role** -- enable or disable IPv4/IPv6 packet forwarding and IPv6 RA based on device role (only for devices that [support multiple roles](dev-device-roles))

For example, Arista EOS needs explicit configuration of IPv4 and IPv6 routing. It also supports system-wide MTU:

```
hostname {{ inventory_hostname.replace("_","-") }}
!
{% if af.ipv4|default(False) %}
ip routing
{% endif %}
{% if af.ipv6|default(False) %}
ipv6 unicast-routing
{% endif %}
!
{% if mtu is defined %}
interface defaults
 mtu {{ mtu }}
{% endif %}
!
```

If we want to support Arista EOS running as router *or host*, we should also check the **role** parameter:

```
{% if af.ipv4|default(False) and role != 'host' %}
ip routing
{% else %}
no ip routing
{% endif %}
{% if af.ipv6|default(False) and role != 'host' %}
ipv6 unicast-routing
{% else %}
no ipv6 unicast-routing
{% endif %}
```

## Loopback Configuration

The device data model assumes every network device has a primary loopback interface. The data model contains these loopback-related parameters:

* **loopback.ipv4** -- IPv4 loopback address in CIDR format when available.
* **loopback.ipv6** -- IPv6 loopback address in CIDR format when available.
* **loopback.ifname** -- Loopback interface name.
* **type** set to `loopback`
* **virtual_interface** set to `True`

```{tip}
You could use the **‌netlab_interfaces** list to configure the loopback interface like any other interface. If you take this approach, you should use the **‌type** or **virtual_interface** attributes to skip interface parameters not applicable to the loopback interface(s) while configuring them.
```

Either address family might be missing -- you have to check the presence of attributes in your configuration templates. Arista EOS example:

```
interface {{ loopback.ifname }}
{% if 'ipv4' in loopback %}
 ip address {{ loopback.ipv4 }}
{% endif %}
{% if 'ipv6' in loopback %}
 ipv6 address {{ loopback.ipv6 }}
{% endif %}
```

When your device does not accept interface addresses in CIDR format, use the **ipaddr** filter to generate the desired address format. Cisco IOS example:

```
interface {{ loopback.ifname }
{% if 'ipv4' in loopback %}
 ip address {{ loopback.ipv4|ipaddr('address') }} {{ loopback.ipv4|ipaddr('netmask') }}
{% endif %}
{% if 'ipv6' in loopback %}
 ipv6 address {{ loopback.ipv6|upper }}
{% endif %}
```

## Management Interface Configuration

If you decide to run LLDP on your device (highly recommended), turn it off on the management interface. The management interface name is specified in **mgmt.ifname** parameter. Nexus OS example:

```
interface {{ mgmt.ifname|default('GigabitEthernet0/0') }}
 no lldp transmit
 no lldp receive
```

## Configuring Interfaces

Data-plane device interfaces are specified in the **interfaces** list. Interface definition always has these parameters:

* **ifname** -- interface name (always present)
* **type** -- link type, for example: `stub` (optional)

It might also have these (optional) parameters:

* **virtual_interface** -- the interface is a virtual interface (loopback, VLAN interface, subinterface...). Use this parameter to skip physical interface configuration (for example, bandwidth)
* **role** -- link role (as set by **role** link attribute)
* **mac** -- interface MAC address when requested by the **features.initial.generate_mac** device setting
* **mtu** -- interface MTU
* **_use_ip_mtu** -- a hint that the interface MTU is lower than the **min_phy_mtu** accepted by your device and that you should configure IPv4/IPv6 MTU instead of interface MTU.
* **bandwidth** -- interface bandwidth
* **name** -- interface description
* **ipv4** -- IPv4 interface address
* **ipv6** -- IPv6 interface address
* **_parent_intf** -- name of the parent interface of unnumbered IPv4 interfaces
* **_parent_ipv4** -- IPv4 address of the parent interface of unnumbered IPv4 interfaces
* **shutdown** -- the interface should be disabled when the lab is started

```{tip}
You can use the **‌netlab_interfaces** instead of the **‌interfaces** list. **‌netlab_interfaces** list includes the loopback interface *‌on devices that are not hosts*, allowing you to configure all interfaces with the same code.
```

**Notes:**

* You don't have to support all interface attributes, but it's highly recommended that interface addresses, the description, and the MTU be implemented.
* Use `if sth is defined`, `sth|default(value)`, or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes. Try to be consistent ;)

The interface part of the initial device configuration template starts with a **for** loop over all configured interfaces:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 no shutdown
{% endfor %}
```

The rest of the interface configuration should check the presence of various attributes you decided to support. Cisco IOS example:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 no shutdown
{% if l.name is defined %}
 description {{ l.name }}
{% endif %}
{% if l.bandwidth is defined %}
 bandwidth {{ l.bandwidth  }}
{% endif %}
{% if l.mtu is defined %}
{%   if l._use_ip_mtu|default(False) %}
 ip mtu {{ l.mtu }}
{%   else %}
 mtu {{ l.mtu }}
{%   endif %}
{% endif %}
{% if 'ipv4' in l %}
...
{% endif %}
{% if 'ipv6' in l %}
...
{% endif %}
!
{% endfor %}
```

When running as a [router](dev-device-roles), your device MUST send IPv6 router advertisements on IPv6-enabled interfaces. When running as a host, it *should* listen to IPv6 router advertisements to get a default route. Arista EOS example:

```
{#
    Set interface IPv6 addresses
#}
{% if 'ipv6' in l %}
{%   if role != 'host' %}
 ipv6 nd ra interval 5
{%   else %}
 ipv6 nd ra rx accept default-route
{%   endif %}
{%   if l.ipv6 is sameas True %}
 ipv6 enable
{%   elif l.ipv6 is string %}
 ipv6 address {{ l.ipv6 }}
{%   endif %}
{% endif %}
```

```{note}
A device that listens to IPv6 RAs in host mode SHOULD have the **features.initial.ipv6.use_ra** [device feature](dev-device-features) set to *‌True*. _netlab_ generates IPv6 static routes for *‌host* nodes without this feature.
```

### Virtual Interfaces

If you have to configure additional parameters on physical interfaces (for example, choosing between switch ports and router interfaces), use the **virtual_interface** parameter to decide whether to include the configuration commands related to physical interfaces. Arista EOS example:

```
{% if l.virtual_interface is not defined %}
!
 mac-address {{ '52dc.cafe.%02x%02x' % ( id,l.ifindex ) }}
{% endif %}
```

You can also check the interface type (`l.type`). It is set to **loopback** for loopback interfaces or **stub** for stub interfaces (interfaces with no neighbors).

### Setting Interface Description

You might want to implement slightly more complex interface descriptions than what _netlab_ generates. For example:

* The interface name is not set on stub interfaces.
* You might want to add a link role to the interface description.

Cisco IOS example:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 no shutdown
{% if l.name is defined %}
 description {{ l.name }}{{ " ["+l.role+"]" if l.role is defined else "" }}
{% elif l.type|default("") == "stub" %}
 description Stub interface
{% endif %}
...
{% endfor %} 
```

### Interface Addresses

If your device supports unnumbered interfaces, IPv4 and IPv6 interface addresses could be specified as strings in CIDR format or as boolean values.

If your device doesn't support unnumbered IPv4 or IPv6 addresses, use a configuration template similar to this one (Linux):

```
{% for l in interfaces|default([]) %}
{% if l.ipv4 is defined %}
ip addr add {{ l.ipv4 }} dev {{ l.ifname }}
{% endif %}
{% if l.ipv6 is defined %}
sysctl -w net.ipv6.conf.{{ l.ifname }}.disable_ipv6=0
ip -6 addr add {{ l.ipv6 }} dev {{ l.ifname }}
{% endif %}
{% endfor %}
```

Coping with unnumbered interfaces requires a slightly more convoluted decision tree (Arista EOS):

```
{% if 'ipv4' in l %}
{%   if l.ipv4 == True %}
 ip address unnumbered {{ l._parent_intf }}
{%   elif l.ipv4|ipv4 %}
 ip address {{ l.ipv4 }}
{%   else %}
! Invalid IPv4 address {{ l.ipv4 }}
{%   endif %}
{% endif %}
!
{% if 'ipv6' in l %}
{%   if l.ipv6 == True %}
 ipv6 enable
{%   elif l.ipv6|ipv6 %}
 ipv6 address {{ l.ipv6 }}
{%   else %}
! Invalid IPv6 address {{ l.ipv6 }}
{%   endif %}
```

Linux-based network operating systems (FRR, Cumulus Linux) set the IPv4 address of an unnumbered IPv4 interface to the IPv4 address of the parent interface. Here's part of the template used to create the `/etc/network/interfaces` file on Cumulus Linux:

```
auto {{ l.ifname }}
{%   if l.ipv4 is defined %}
iface {{ l.ifname }} inet static
{%     if l.ipv4 == True %}
{%       if l._parent_ipv4 is defined %}
  address {{ l._parent_ipv4 }}
{%       endif %}
{%     else %}
  address {{ l.ipv4 }}
{%     endif %}
{%   endif %}
```

This is the relevant part of the template that configures unnumbered IPv4 interfaces on FRR:

```
interface {{ l.ifname }}
{% if l.ipv4 is defined and (l.ipv4 is string or l._parent_ipv4 is defined) %}
 ip address {{ l.ipv4 if l.ipv4 is string else l._parent_ipv4 }}
{% else %}
 ! no ip address
{% endif %}
```

### Setting Interface MAC Address

The interface MAC address is not part of the device data model. If you have to set it (for example, Arista EOS requires a unique MAC address on every interface), use device ID (**id**) and interface index (**ifdata.ifindex** in interface data) in a configuration template similar to this one:

```
{% for ifdata in interfaces %}
interface {{ ifdata.ifname }}
 mac-address {{ '52dc.cafe.%02x%02x' % ( id,ifdata.ifindex ) }}
!
{% endfor %}
```

### Configuring IPv6 RA Parameters

If you decide to implement [IPv6 RA parameters](links-ra), you might appreciate these hints:

* RA parameters have to be processed whenever **ipv6** attribute is set (*string* or *True*) and the node **role** is **router**. RA parameters do not apply to **host** or **bridge** nodes.
* Do not expect any parameters to be set; always work with default values.
* If **ra.disable** is **true** (default: false), disable RA and move on. Otherwise, enable IPv6 RA and set the RA interval to some small value (for example, 5 seconds).
* If **ipv6** attribute is a real address (not *True*), check the **ra.slaac** (default: *True*) and **ra.onlink** (default: *True*) parameters. The **ipv6** attribute is a CIDR *address* ; use `intf.ipv6|ipaddress(0)` to get the prefix.
* Set further RA flags if **ra.dhcp** is set (regardless of the value of the **ipv6** attribute).

This is the FRRouting implementation of the above hints:

```
{% if i.ipv6 is defined %}
{%   if i.ipv6 is string and i.ipv6|ipv6 %}
 ipv6 address {{ i.ipv6 }}
{%   endif %}
{%   if i.type != 'loopback' and role == 'router' %}
{%     if i.ra.disable|default(false) is true %}
 ipv6 nd suppress-ra
{%     else %}
 ipv6 nd ra-interval 5
 no ipv6 nd suppress-ra
{%     endif %}
{%     if 'ra' in i and i.ipv6 is string %}
{%       if i.ra.slaac|default(true) is false %}
 ipv6 nd prefix {{ i.ipv6|ipaddr(0) }} no-autoconfig
{%       endif %}
{%       if i.ra.onlink|default(true) is false %}
 ipv6 nd prefix {{ i.ipv6|ipaddr(0) }} off-link
{%       endif %}
{%     endif %}
{%     if i.ra.dhcp|default(false) == 'all' %}
 ipv6 nd managed-config-flag
{%     endif %}
{%     if i.ra.dhcp|default(false) == 'other' %}
 ipv6 nd other-config-flag
{%     endif %}
{%   endif %}
{% endif %}
```

```{tip}
* FRRouting does not send RA messages by default (RA has to be explicitly enabled). If your device sends the RA messages by default, change the initial tests to `if ra.disabled is true or role != 'router'`.
* On devices that send RA messages by default, configure RA parameters before configuring IPv6 addresses (you don't want the device to send a spurious RA before the RA parameters are configured).
```

## Setting Static Host Names (Optional)

Your device might support static host-to-address mapping. If that's the case, configuring it is worthwhile -- users troubleshooting their configurations might appreciate seeing hostnames instead of IP addresses.

[Ansible output module](../../outputs/ansible.md) creates a dictionary mapping node names to IPv4/IPv6 address lists. The first address in the list is the loopback IP address (assuming the node has a loopback interface). Here's a sample dictionary for a small lab with a router and two hosts:

```
hosts:
  relay:
    ipv4:
    - 10.0.0.1
    - 172.16.0.1
    - 172.16.1.1
    - 172.16.2.1
    - 172.16.3.1
  s1:
    ipv4:
    - 172.16.2.6
  s2:
    ipv4:
    - 172.16.3.7
```

**Notes:**
* The **hosts** dictionary contains a device only when that device has a usable IPv4 or IPv6 address. An entry in the **hosts** dictionary will have at least one key.
* The device entry contains an address family only when it has a usable IP address in that address family. **ipv4** and **ipv6** values are never empty lists.

If your device supports a single IP address associated with a statically configured host, use this template (Nexus OS):

```
{% for hname,hdata in hosts.items() if 'ipv4' in hdata and hname != inventory_hostname %}
ip host {{ hname }} {{ hdata.ipv4[0] }}
{% endfor %}
```

**Notes:**

* The configuration template iterates over all devices with usable IP addresses
* It skips the current device or devices that don't have the IPv4 address family configured
* For all other devices, it takes the first IPv4 address in the list of IPv4 addresses and configures that as the static DNS entry.

If your device supports multiple IP addresses associated with a single hostname, use this template (Arista EOS):

```
{% for hname,hdata in hosts.items() if 'ipv4' in hdata and hname != inventory_hostname %}
ip host {{ hname|replace('_','') }} {{ hdata.ipv4|join (' ') }}
{% endfor %}
{% for hname,hdata in hosts.items() if 'ipv6' in hdata and hname != inventory_hostname %}
ipv6 host {{ hname|replace('_','') }} {{ hdata.ipv4|join (' ') }}
{% endfor %}
```

Use the following template if your device expects IPv4 and IPv6 addresses listed in the same line (Cisco IOS):

```
{% for hname,hdata in hosts.items() if hname != inventory_hostname %}
{%   set addr_list = hdata.ipv4|default([]) + hdata.ipv6|default([]) %}
ip host {{ hname }} {{ addr_list|join (' ') }}
{% endfor %}
```
(initial-ansible-config)=
## Using Ansible Configuration Modules

You might be forced to use Ansible configuration modules instead of generating and deploying a device configuration from a Jinja2 template. In that case, create the list of Ansible tasks needed to configure your device in `netsim/tasks/<nos>/initial.yml` with **nos** being the value of **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.

Fortinet example (**vdom** variable is set as an Ansible group variable in system settings):

```
---
- name: Configure global attributes
  fortinet.fortios.fortios_system_global:
    vdom: "{{ vdom }}"
    system_global:
      hostname: '{{ inventory_hostname.replace("_","-") }}'

- name: Turn off LLDP on management interface
  fortinet.fortios.fortios_system_interface:
    vdom: "{{ vdom }}"
    state: "present"
    system_interface:
      interface: "port1"
      lldp_reception: "disable"
      lldp_transmission: "disable"
      name: "port1"

- name: Configure loopback interface
  fortinet.fortios.fortios_system_interface:
    vdom: "{{ vdom }}"
    state: "present"
    system_interface:
      interface: "loopback0"
      ip: "{{ loopback.ipv4 | default(omit) }}"
      name: "loopback0"
      type: "loopback"
      vdom: "{{ vdom }}"
  when: loopback is defined

- name: Configure loopback description
  fortinet.fortios.fortios_system_interface:
    vdom: "{{ vdom }}"
    system_interface:
      alias: '{{ loopback.name.replace(">","-") }}'
      interface: "loopback0"
      name: "loopback0"
      vdom: "{{ vdom }}"
  when: loopback.name is defined

... more tasks...
```

(dev-config-initial-tests)=
## Integration Tests

You can use the following integration tests in the `tests/integration/initial` directory to test your implementation:

* **01-interfaces.yml** -- basic interface parameters, including IPv6 addresses, MTU and bandwidth
* **02-loopback.yml** -- additional loopback interfaces
* **03-unnumbered.yml** -- unnumbered IPv4 and IPv6 interfaces (no validation)
* **04-mtu.yml** -- setting MTUs
* **05-host.yml** -- Device running in *host* mode -- no IP forwarding, no IPv6 RAs
* **06-bridge.yml** -- Device running in *bridge* mode -- multiple layer-2 forwarding domains, no IP access to the device.
* **07-router.yml** -- Device running in *router* mode -- IP forwarding, IPv6 RAs

To use an integration test to test your configuration templates:

* Execute `netlab up --no-config -d <device> <topology-name>` to start the lab without configuring the devices.
* Execute `netlab initial -o` to create device configurations in the `config` directory.
* Inspect device configurations before proceeding.
* Execute `netlab initial` to deploy device configurations
* Execute `netlab validate` to run validation tests

To use an integration test in a CI/CD pipeline, execute `netlab up -d <device> <topology-name> --validate`.
