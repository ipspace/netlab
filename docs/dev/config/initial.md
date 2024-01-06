# Initial Device Configuration

This document describes the device data model parameters one should consider when creating an initial device configuration template. For a wider picture, please see [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [Using Ansible Configuration Modules](initial-ansible-config) section at the bottom of this document.

The device configuration template (in Jinja2 format) should be stored in `netsim/templates/initial/<nos>.j2` with **nos** being the value of **netlab_device_type** or  **ansible_network_os** Ansible variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Device Parameters

You can use several device settings (specified in [device parameter file](dev-device-parameters)) to indicate which optional initial device configuration features your device supports:

```
loopback_interface_name: Loopback{ifindex}
features:
  initial:
    system_mtu: True
    ipv4:
      unnumbered: True
    ipv6:
      lla: True
```

* **loopback_interface_name** -- Loopback interface name template. Use `{ifindex}` to insert interface number.
* **features.initial.system_mtu** -- The device supports system MTU settings
* **features.initial.ipv4.unnumbered** -- The device supports unnumbered IPv4 interfaces. The IP address of the primary loopback interface should be used as the IPv4 address of those interfaces.
* **features.initial.ipv6.lla** -- The device supports IPv6 interfaces using just link-local addresses.

## Static Configuration

Your device template should start with the static configuration needed to make your device usable. You might want to configure all relevant parameters or rely on box-building instructions to get the initial configuration set up.

For example, the Cisco IOS configuration template enables LLDP, disables DNS lookup, and removes banners:

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

* **inventory_hostname** -- device name. You might need to remove special characters (underscore, dots...) from device name.
* **af.ipv4** and **af.ipv6** -- global flags indicating whether IPv4 or IPv6 is enabled on this device.
* **mtu** -- system-wide MTU (when supported by the device)

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

## Loopback Configuration

The device data model assumes every network device has a primary loopback interface. The data model contains these loopback-related parameters:

* **loopback.ipv4** -- IPv4 loopback address in CIDR format when available.
* **loopback.ipv6** -- IPv6 loopback address in CIDR format when available.
* **loopback.ifname** -- Loopback interface name for devices with `loopback_interface_name` parameter.

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

If your device does not accept interface addresses in CIDR format, use **ipaddr** filter to generate the desired address format. Cisco IOS example:

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

If you decide to run LLDP on your device (highly recommended), disable it on the management interface. The management interface name SHOULD be specified in **mgmt.ifname** parameter; use a default value just in case something went wrong. Nexus OS example:

```
interface {{ mgmt.ifname|default('GigabitEthernet0/0') }}
 no lldp transmit
 no lldp receive
```

## Configuring Interfaces

Data-plane device interfaces are specified in the **interfaces** list. Each interface might have these parameters:

* **ifname** -- interface name (always present)
* **type** -- link type, for example: `stub` (optional)
* **virtual_interface** -- the interface is a virtual interface (loopback, VLAN interface, subinterface...). Use this parameter to skip physical interface configuration (for example, bandwidth)
* **role** -- link role (as set by **role** link attribute -- optional)
* **mtu** -- interface MTU (optional)
* **bandwidth** -- interface bandwidth (optional)
* **name** -- interface description (optional)
* **ipv4** -- IPv4 interface address (optional)
* **ipv6** -- IPv6 interface address (optional)
* **_parent_intf** -- name of the parent interface of unnumbered IPv4 interfaces
* **_parent_ipv4** -- IPv4 address of the parent interface of unnumbered IPv4 interfaces

**Notes:**

* You don't have to support all interface attributes, but it's highly recommended to implement interface addresses, interface description, and MTU.
* Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes. Try to be consistent ;)

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
 ip mtu {{ l.mtu }}
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

### Virtual Interfaces

If you have to configure additional parameters on physical interfaces (for example, choosing between switch ports and router interfaces), use the **virtual_interface** parameter to decide whether to include the configuration commands related to physical interfaces. Arista EOS example:

```
{% if l.virtual_interface is not defined %}
!
 mac-address {{ '52dc.cafe.%02d%02d' % ( id,l.ifindex ) }}
{% endif %}
```

### Setting Interface Description

You might want to implement slightly more complex interface descriptions than what _netlab_ generates. For example:

* Interface name is not set on stub interfaces.
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

### Minimum Interface MTU

Some devices have weird MTU rules. For example, CSR 1000V cannot set the L2 MTU below 1500 bytes or the L3 MTU above 1500 bytes. You could use the **min_mtu** device setting in those scenarios and generate MTU configuration accordingly.

Cisco IOS example:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 no shutdown
{% if l.mtu is defined %}
{%   if min_mtu is defined and min_mtu > l.mtu %}
 ip mtu {{ l.mtu }}
{%   else %}
 mtu {{ l.mtu }}
{%   endif %}
{% endif %}
{% endfor %}
```

### Interface Addresses

IPv4 and IPv6 interface addresses could be specified as strings in CIDR format or as boolean values if your device supports unnumbered interfaces.

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

Linux-based network operating systems (FRR, Cumulus Linux) set the IPv4 address of an unnumbered IPv4 interface to the IPv4 address of the parent interface. Here's part of the template used to create `/etc/network/interfaces` file on Cumulus Linux:

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

The interface MAC address is not part of the device data model. If you have to set it (for example, Arista EOS requires a unique MAC address on every interface), use device ID (**id**) and interface index (**ifindex** in interface data) in a configuration template similar to this one:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 mac-address {{ '52dc.cafe.%02d%02d' % ( id,l.ifindex ) }}
!
{% endfor %}
```

## Setting Static Host Names (Optional)

Your device might support static host-to-address mapping. If that's the case, it's worthwhile configuring it -- users troubleshooting their configurations might appreciate seeing hostnames instead of IP addresses.

If your device supports a single IP address associated with a statically configured host, use this template (Nexus OS):

```
{% for k,v in hostvars.items() if k != inventory_hostname and v.af.ipv4|default(False) %}
{%   if v.loopback.ipv4 is defined %}
ip host {{ k }} {{ v.loopback.ipv4|ipaddr('address') }}
{%   elif v.interfaces|default([]) and v.interfaces[0].ipv4 is defined %}
ip host {{ k }} {{ v.interfaces[0].ipv4|ipaddr('address') }}
{%   endif %}
{% endfor %}
```

Equivalent Junos template:

```
system {
  host-name {{ inventory_hostname }}
    static-host-mapping {
{% for k,v in hostvars.items() if k != inventory_hostname %}
{%   if v.loopback.ipv4 is defined %}
        {{ k|replace('_','') }} inet {{ v.loopback.ipv4|ipaddr('address') }};
{%   elif v.interfaces|default([]) and v.interfaces[0].ipv4 is defined %}
        {{ k|replace('_','') }} inet {{ v.interfaces[0].ipv4|ipaddr('address') }};
{%   endif %}
{% endfor %}
    }
}
```

**Notes:**

* The configuration template iterates over all devices known to Ansible
* It skips the current device or devices that don't have IPv4 address family configured
* For all other devices, it takes the loopback IPv4 address or the IPv4 address of the first interface and configures that as the static DNS entry.

If your device supports multiple IP addresses associated with a single hostname, use this template (Cisco IOS). Take the template as-is, and don't try to optimize it... it's been hard enough to make it work with Jinja2 whitespace rules ;)

```
{% for k,v in hostvars.items() if k != inventory_hostname and v.af.ipv4|default(False) %}
ip host {{ k }}{% if v.loopback.ipv4 is defined %} {{ v.loopback.ipv4|ipaddr('address') }}{% endif %}
{%- for l in v.interfaces|default([]) if 'ipv4' in l and l.ipv4 != True and l.ipv4|ipv4 %} {{ l.ipv4|ipaddr('address') }}{% endfor %}

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

## Integration Tests

You can use the following integration tests in `tests/integration/initial` directory to test your implementation:

* **interfaces.yml** -- basic interface parameters, including IPv6 addresses, MTU and bandwidth
* **loopback.yml** -- additional loopback interfaces
* **unnumbered.yml** -- unnumbered IPv4 and IPv6 interfaces

To use an integration test to test your configuration templates:

* Execute `netlab up --no-config -d <device> <topology-name>` to start the lab without configuring the devices.
* Execute `netlab initial -o` to create device configurations in `config` directory.
* Inspect device configurations before proceeding.
* Execute `netlab initial` to deploy device configurations

To use an integration test in a CI/CD pipeline, execute `netlab up -d <device> <topology-name>`.
