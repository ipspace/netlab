# Initial Device Configuration

This document describes the device data model parameters one should consider when creating an initial device configuration template. For a wider picture, please see [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [Using Ansible Configuration Modules](initial-ansible-config) section at the bottom of this document.

The device configuration template (in Jinja2 format) should be stored in `netsim/templates/initial/<nos>.j2` with **nos** being the value of **netlab_device_type** or  **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Static Configuration

Your device template should start with static configuration needed to make your device usable. You might want to configure all relevant parameters or rely on box-building instructions to get the initial configuration set up.

For example, Cisco IOS configuration template enables LLDP, disable DNS lookup and removes banners:

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

The device data model assumes a single loopback interface with unspecified name (the loopback interface name should be set in the configuration template). The data model may contains these optional loopback-related parameters:

* **loopback.ipv4** -- IPv4 loopback address in CIDR format
* **loopback.ipv6** -- IPv6 loopback address in CIDR format.

Either address family might be missing -- you have to check the presence of attributes in your configuration templates. Arista EOS example:

```
interface Loopback0
{% if 'ipv4' in loopback %}
 ip address {{ loopback.ipv4 }}
{% endif %}
{% if 'ipv6' in loopback %}
 ipv6 address {{ loopback.ipv6 }}
{% endif %}
```

If your device does not accept interface addresses in CIDR format, use **ipaddr** filter to generate the desired address format. Cisco IOS example:

```
interface Loopback0
{% if 'ipv4' in loopback %}
 ip address {{ loopback.ipv4|ipaddr('address') }} {{ loopback.ipv4|ipaddr('netmask') }}
{% endif %}
{% if 'ipv6' in loopback %}
 ipv6 address {{ loopback.ipv6|upper }}
{% endif %}
```

## Management Interface Configuration

If you decided to run LLDP on your device (highly recommended), disable it on the management interface. The management interface name SHOULD be specified in **mgmt.ifname** parameter; use a default value just in case something went wrong. Nexus OS example:

```
interface {{ mgmt.ifname|default('GigabitEthernet0/0') }}
 no lldp transmit
 no lldp receive
```

## Configuring Interfaces

Device interfaces are specified in the **interfaces** list. Each interface might have these parameters:

* **ifname** -- interface name (always present)
* **type** -- link type, for example: `stub` (optional)
* **role** -- link role (as set by **role** link attribute -- optional)
* **mtu** -- interface MTU (optional)
* **bandwidth** -- interface bandwidth (optional)
* **name** -- interface description (optional)
* **ipv4** -- IPv4 interface address (optional)
* **ipv6** -- IPv6 interface address (optional)

**Notes:**

* You don't have to support all interface attributes, but it's highly recommended to implement interface addresses, description and MTU.
* Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)

Interface part of initial device configuration template starts with a **for** loop over all configured interfaces:

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

### Setting Interface Name

You might want to implement slightly more complex interface descriptions. For example:

* Interface name is not set on stub interfaces.
* You might want to add link role to the interface description.

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

Some devices have weird MTU rules. For example, CSR 1000V cannot set the L2 MTU below 1500 bytes or L3 MTU above 1500 bytes. You could use **min_mtu** device setting in those scenarios and generate MTU configuration accordingly.

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

IPv4 and IPv6 interface addresses could be specified as strings in CIDR format or as boolean value if your device supports unnumbered interfaces.

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
 ip address unnumbered Loopback 0
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

### Setting Interface MAC Address

Interface MAC address is not part of the device data model. If you have to set it (for example, Arista EOS requires a unique MAC address on every interface), use device ID (**id**) and interface index (**ifindex** in interface data) in a configuration template similar to this one:

```
{% for l in interfaces %}
interface {{ l.ifname }}
 mac-address {{ '52dc.cafe.%02d%02d' % ( id,l.ifindex ) }}
!
{% endfor %}
```

## Setting Static Host Names (Optional)

Your device might support static host-to-address mapping. If that's the case, it's worthwhile configuring it -- users troubleshooting their configurations might appreciate seeing host names instead of IP addresses.

If your device supports a single IP address associated to a statically configured host, use this template (Nexus OS):

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

If your device supports multiple IP addresses associated with a single hostname, use this template (Cisco IOS). Take the template as-is and don't try to optimize it... it's been hard enough to make it work with Jinja2 whitespace rules ;)

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
