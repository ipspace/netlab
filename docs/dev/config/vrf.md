# Configuring VRFs

This document describes the device data model parameters one should consider when creating a VRF configuration template. For a wider picture, please see [](../device-features.md) or [](../devices.md).

This document assumes you're using an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build device configuration, you'll find some guidance in [Using Ansible Configuration Modules](ospf-ansible-config) section of OSPF implementation guide.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/vrf/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Data Model

VRFs used on a device are defined in the **vrfs** dictionary. Dictionary keys are VRF names, dictionary values are dictionaries of VRF parameters which can contain these elements:

* **rd** -- VRF route distinguisher
* **import** -- list of import route targets
* **export** -- list of export route targets
* **af** -- list of address families (`ipv4` and/or `ipv6`) used by the VRF
* **ospf** -- VRF OSPF parameters (when there's an OSPF routing process running in the VRF)
* **bgp** -- VRF BGP parameters (when the VRF contains at least one CE router running BGP) 

Other parameters:

* VRF interfaces have **vrf** interface parameter that contains VRF name.
* OSPF parameters within the **vrfs._vrf-name_.ospf** dictionary are identical to global OSPF parameters
* BGP parameters within the **vrfs._vrf-name_.bgp** dictionary are identical to global BGP parameters. You will need to focus on **networks** (networks to be announced in per-VRF BGP AF) and **neighbors** (BGP sessions with CE routers)

## Device Features

The only configurable VRF-related feature is the name of in-VRF loopback interface -- you can specify it in `devices.<device>.loopback_interface_name`. Use **ifindex** variable to create unique loopback interfaces (**ifindex** will be set to VRF index when creating VRF loopback interfaces).

Cisco IOS example:

```
devices:
  iosv:
    loopback_interface_name: Loopback{ifindex}
```

## VRF Configuration Principles

Many network devices lose interface IP addresses when you configure a VRF on the interface. Interface VRF membership should therefore be configured before interface IP addresses -- in the **initial** phase of device configuration.

In most cases, you have to create VRFs before you can use them in interface configuration. The best way to configure VRFs is thus:

* Create VRFs in `netsim/templates/initial/<nos>.vrf.j2` template.
* Invoke that template in `netsim/templates/initial/<nos>.j2` template whenever the device data contains **vrfs** dictionary.
* Configure interface VRF membership as part of the standard interface configuration
* Configure other VRF features (OSPF, BGP) in `netsim/templates/vrf/<nos>.j2` template

## Create VRFs

In the _create VRF_ template (stored in `netsim/templates/initial/<nos>.vrf.j2`) iterate over the **vrfs** dictionary and configure VRFs.

Cisco IOS configures most VRF parameters (RD, RT) in the VRF definition, and uses address families within VRF definition to enable IPv6 and/or IPv6 in the VRF:

```
{% for vname,vdata in vrfs.items() %}
vrf definition {{ vname }}
 rd {{ vdata.rd }}
{%   for rt in vdata.import %}
 route-target import {{ rt }}
{%   endfor %}
{%   for rt in vdata.export %}
 route-target export {{ rt }}
{%   endfor %}
!
{%   for af in ['ipv4','ipv6'] if af in vdata.af %}
 address-family {{ af }}
 exit-address-family
!
{%   endfor %}
{% endfor %}
```

Arista EOS defines RD in the VRF definition (route targets are defined in the BGP routing process). It also requires **ip routing** enabled for individual VRFs:

```
{% for vname,vdata in vrfs.items() %}
vrf instance {{ vname }}
 rd {{ vdata.rd }}
!
{% if 'ipv4' in vdata.af %}
ip routing vrf {{ vname }}
!
{% endif %}
{% if 'ipv6' in vdata.af %}
ipv6 routing vrf {{ vname }}
!
{% endif %}
{% endfor %}
```

Include the VRF creation template in `netsim/templates/initial/<nos>.j2` template:

```
{% if vrfs is defined %}
{% include '<nos>.vrf.j2' %}
{% endif %}
```

Finally, put interfaces into VRFs based on **vrf** interface parameter within the interface configuration part of `netsim/templates/initial/<nos>.j2`. For example:

```
{% for l in interfaces|default([]) %}
interface {{ l.ifname }}
 no shutdown
{% if l.vrf is defined %}
 vrf forwarding {{ l.vrf }}
{% endif %}
...
{% endfor +%}
```

## Configuring Other VRF Features

Depending on the VRF-aware routing protocols supported by your platform you might have to configure per-VRF OSPF routing processes or VRF BGP address families.

You can configure all of these features in `netsim/templates/vrf/<nos>.j2` template, or use a more structured approach:

* Configure per-VRF OSPF routing process in `netsim/templates/vrf/<nos>.ospfv2.j2` and/or `netsim/templates/vrf/<nos>.ospfv3.j2`
* Configure VRF BGP address families in `netsim/templates/vrf/<nos>.bgp.j2`
* Include these templates in `netsim/templates/vrf/<nos>.j2` template based on presence of **bgp.as** attribute (the device is running BGP) or **ospf** attribute of a VRF dictionary (VRF is running OSPF)

Cisco IOS example:

```
{% if bgp.as is defined %}
{% include 'ios.bgp.j2' %}
{% endif %}
{% for vname,vdata in vrfs.items() if 'ospf' in vdata %}
{%   include 'ios.ospfv2-vrf.j2' %}
{% endfor %}
```

### Configuring BGP

In the BGP configuration process, configure VRF address families, OSPF-to-BGP redistribution, redistribution of connected interfaces, and advertise VRF-specific networks.

Cisco IOS has different address families for IPv4-in-VRF and IPv6-in-VRF.

```
{% import "ios.bgp-macro.j2" as bgpcfg %}
!
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
{%   for af in ('ipv4','ipv6') if af in vdata.af %}
 address-family {{ af }} vrf {{ vname }}
  redistribute connected
{%     if af == 'ipv4' and 'ospf' in vdata %}
  redistribute ospf {{ vdata.vrfidx }}
{%     endif %}
!
{%     for n in vdata.networks|default([]) if af in n %}
{{       bgpcfg.bgp_network(af,n[af]) }}
{%     endfor %}
!
... BGP neighbors ...
{% endfor %}
```

**Note:** Cisco IOS template uses a macro to configure BGP network advertisement. See [](dev-config-vrf-bgp) for more details.

Arista EOS has VRF BGP configuration mode where you specify both IPv4 and IPv6 route targets. You have to enable individual address families within that configuration mode:

```
mpls ip
!
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
!
 vrf {{ vname }}
  redistribute connected
  router-id {{ bgp.router_id }}
  rd {{ vdata.rd }}
{%   if 'ospf' in vdata %}
  redistribute ospf
{%   endif %}
{%   for af in ['ipv4','ipv6'] if af in vdata.af %}
{%     for rt in vdata.import %}
  route-target import vpn-{{ af }} {{ rt }}
{%     endfor %}
{%     for rt in vdata.export %}
  route-target export vpn-{{ af }} {{ rt }}
{%     endfor %}
{%   endfor %}
{%   for af in ['ipv4','ipv6'] %}
{%     for n in vdata.networks|default([]) if af in n %}
{%       if loop.index == 1 %}
  address-family {{ af }}
{%       endif %}
   network {{ n[af]|ipaddr('0') }}
{%     endfor %}
{%   endfor %}
... BGP neighbors ...
{% endfor %}
```

(dev-config-vrf-bgp)=
### Configure BGP Neighbors

You could copy the BGP configuration template into the `vrf` directory and modify it to configure in-VRF BGP neighbors, or you could create a symbolic link to the Jinja2 template containing the BGP neighbor configuration macro (if it exists for your platform) within the `bgp` directory and use common code to configure BGP neighbors. The latter approach is recommended as it ensures feature parity between global- and in-VRF BGP neighbors.

To configure BGP neighbors, iterate over the **vrfs._vname_.bgp.neighbors** dictionary and configure the neighbors. Cisco IOS configuration syntax results in a streamlined process:

```
{% import "ios.bgp-macro.j2" as bgpcfg %}
!
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
{%   for af in ('ipv4','ipv6') if af in vdata.af %}
 address-family {{ af }} vrf {{ vname }}
... other BGP parameters ...
{%     for n in vdata.bgp.neighbors|default([]) if af in n %}
{{       bgpcfg.neighbor_global(n,n[af]) }}
{{       bgpcfg.neighbor_af(n,n[af],bgp) }}
{%     endfor %}
{%   endfor %}
{% endfor %}
```

Arista EOS is a bit more complex: BGP neighbors are defined in the BGP VRF configuration mode and activated within the in-VRF address family:

```
{% import "eos.bgp-macro.j2" as bgpcfg %}
!
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
!
 vrf {{ vname }}
... other BGP parameters ...
{%   for n in vdata.bgp.neighbors|default([]) %}
{%     for af in ['ipv4','ipv6'] if n[af] is defined %}
{{       bgpcfg.neighbor(n,n[af],bgp) }}
{%     endfor %}
{%   endfor %}
{%   for af in ['ipv4','ipv6'] %}
... other AF parameters ...
{%     for n in vdata.bgp.neighbors|default([]) if n[af] is defined %}
{%       if loop.index == 1 %}
  address-family {{ af }}
{%       endif %}
   neighbor {{ n[af] }} activate
{%     endfor %}
{%   endfor %}
{% endfor %}
```

### Configure OSPF

You could use the same _shared macro_ approach to configure VRF OSPF interface, but it's probably simpler to just copy-paste the [global OSPF configuration code](ospf.md) and change OSPF process ID (or a similar configuration construct) to refer to in-VRF OSPF process:

* The main VRF template uses **vdata** variable to refer to the VRF parameters -- OSPF parameters are available within **vdata.ospf** dictionary.
* Use **vdata.vrfidx** as the OSPF process ID
* Use **vdata.ospf.router_id** (or **ospf.router_id**) to set the router ID
* Redistribute BGP into OSPF if the **bgp.as** parameter is set (the device is running BGP)
* You don't have to redistribute connected subnets into OSPF -- interfaces that should be included in the OSPF process will be listed in the **vdata.ospf.interfaces** list.
* Use global **ospf.reference_bandwidth**

The list of OSPF-enabled VRF interfaces is in **vdata.ospf.interfaces** list. Use that list in the same way you'd use the global **ospf.interfaces** list.

Cisco IOS example (Arista EOS example is almost identical):

```
!
router ospf {{ vdata.vrfidx }} vrf {{ vname }}
 router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}
{% if ospf.reference_bandwidth is defined %}
 auto-cost reference-bandwidth {{ ospf.reference_bandwidth }}
{% endif %}
{% for l in vdata.ospf.interfaces|default([]) if l.ospf.passive|default(False) %}
 passive-interface {{ l.ifname }}
{% endfor %}
{% if bgp.as is defined %}
 redistribute bgp {{ bgp.as }} subnets
{% endif %}
!
{% for l in vdata.ospf.interfaces|default([]) if 'ospf' in l and 'ipv4' in l %}
interface {{ l.ifname }}
! {{ l.name|default("") }}
 ip ospf {{ vdata.vrfidx }} area {{ l.ospf.area }}
{%   if l.ospf.network_type is defined %}
 ip ospf network {{ l.ospf.network_type }}
{%   endif %}
{%   if l.ospf.cost is defined %}
 ip ospf cost {{ l.ospf.cost }}
{%   endif %}
{%   if l.ospf.bfd|default(False) %}
 ip ospf bfd
{%   endif %}
!
{% endfor %}
```
