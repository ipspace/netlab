(dev-config-rip)=
# Configuring RIPv2/RIPng

This document describes the device data model parameters used in RIP device configuration templates. Please see [contributing new devices](../devices.md) document for a wider picture.

The document assumes you use an Ansible task list that can deploy device configuration from a template. If you have to use Ansible modules to configure RIP, see the [Configuring OSPF with Ansible Configuration Modules](dev-ospf-ansible-config) section for more details.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/rip/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details).
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)`, or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-rip-features)=
## Device Features

You can use the following **features.ripv2** [device features](dev-device-features) to specify which RIPv2/RIPng features your configuration template implements:

* **ipv4** -- The template configures RIPv2
* **ipv6** -- The template configures RIPng
* **import** -- The list of routing protocols that can be redistributed into RIPv2/RIPng (add `vrf` to the list if you implemented the redistribution in VRFs)
* **passive** -- The template can configure passive interfaces

(dev-rip-af)=
## Supporting Multiple Address Families

The **ripv2.af** variable contains a dictionary of address families configured on the device. It is present in node and VRF data structures.

* **ripv2.af.ipv4** -- there is at least one interface that needs RIPv2 configuration
* **ripv2.af.ipv6** -- there is at least one interface on that needs RIPng configuration

RIP configuration is usually pretty simple; you could structure your template like this:

```
{%   if ripv2.af.ipv4|default(False) %}
router rip
 version 2
 no auto-summary
...
{%   endif %}
!
{%   if ripv2.af.ipv6|default(False) %}
ipv6 router rip default
...
{%   endif %}
```

## Global Configuration

**ripv2** configuration module sets these parameters in the node/VRF **ripv2** dictionary:

* **af.ipv4** (see above) -- configuration template should configure RIPv2
* **af.ipv6** (see above) -- configuration template should configure RIPng
* **bfd.ipv4** -- Use BFD with RIPv2
* **bfd.ipv6** -- Use BFD with RIPng
* **timers.update** -- update timer
* **timers.timeout** -- timeout (route expiration) timer
* **timers.garbage** -- garbage collection timer
* **import** -- route redistribution into RIPv2/RIPng

```{tip}
* All parameters are optional and might not be present
* If the **timers** element is present in the **ripv2** dictionary, the **ripv2** module ensures all three timers are present.
```

## Interface Configuration

Use the **netlab_interfaces** variable (a list containing non-VRF interfaces and the global loopback) to configure non-VRF interfaces and the **vrfs._name_.ripv2.interfaces** to configure VRF interfaces. If you pass the **ripv2** data structure into a macro (see *[](dev-rip-vrf)*), use `ripv2.interfaces|default(netlab_interfaces)` to get the lists of relevant interfaces.

Your template should configure all interfaces in the above list with the **ripv2** attribute. The AF-specific code (for example, using different commands for RIPv2 and RIPng) should also check the relevant interface address family.

Here's a typical configuration procedure:

```
{%     for intf in ripv2.interfaces|default(netlab_interfaces) if 'ripv2' in intf and 'ipv6' in intf %}
!
interface {{ intf.ifname }}
  ipv6 rip default enable
{%     endfor %}
```

**ripv2** configuration module sets these interface parameters in the interface **ripv2** dictionary:

* **ripv2.passive** (True/False) -- is the interface passive?

All interface parameters are optional.

(dev-rip-vrf)=
## Configuring RIPv2/RIPng in VRFs

You have to set these device **features** if you plan to implement RIPv2/RIPng in VRFs:

* **features.vrf.ripv2** -- your template supports VRF-aware RIPv2
* **features.vrf.ripng** -- your template supports VRF-aware RIPng

Most devices use a similar RIPv2/RIPng configuration for the global and the VRF routing processes. It thus makes sense to use a single macro that creates the global- or VRF configuration. You can use an approach similar to this one:

1. Define a configuration macro in the **ripv2/_device_.j2** configuration template. Use `netlab_interfaces` as the default value for `ripv2.interfaces` to get the global- or VRF interface list. Alternatively, add the `interfaces` macro parameter and pass `netlab_interfaces` or `ripv2.interfaces` as the value of that parameter.

```
{% macro config(ripv2,vrf='') -%}
# RIPv2/RIPng configuration
{% endmacro %}
```

```{tip}
The macro might need additional parameters to support route redistribution. For example, Cisco IOS needs the BGP ASN or the OSPF process ID to configure redistribution from BGP or OSPF.
```

2. Invoke the macro from the **ripv2/_device_.j2** template, using global **ripv2** data.

```
...
{{ config(ripv2) }}
```

3. Import the RIPv2 template into the VRF configuration template (the **with context** part gives the imported template access to global variables like `netlab_interfaces`)

```
{% import "templates/ripv2/_device_.j2" as ripv2 with context %}
```

4. When appropriate, call the `ripv2.config` macro from the VRF configuration:

```
{% for vname,vdata in vrfs.items() if vdata.ripv2 is defined %}
{{   ripv2.config(ripv2=vdata.ripv2,vrf=vname) }}
{% endfor %}
```
