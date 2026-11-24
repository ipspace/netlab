(dev-config-vrf)=
# Configuring VRFs

This document describes the device data model parameters one should consider when creating a VRF configuration template. For a wider picture, please see the [contributing new devices](dev-new-devices) document.

This document assumes you're using an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build device configuration, you'll find some guidance in the [Using Ansible Configuration Modules](dev-ospf-ansible-config) section of the OSPF implementation guide.

**Notes:**

* The VRFs and the interface VRF membership are configured in the initial device configuration (see [](dev-vrf-principles)). The routing protocols running in VRFs are configured in the VRF configuration template stored in `netsim/ansible/templates/vrf/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](dev-devices-ansible-vars) for more details).
* The VRF configuration template is applied after the VLAN, OSPF, IS-IS, BGP, and MPLS configuration templates.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-vrf-features)=
## Device Features

You can use the following **features.vrf** [device features](dev-device-features) to specify which VRF features your configuration templates implement.

* **ospfv2**, **ospfv3** -- The templates configure OSPFv2 or OSPFv3 instances in VRFs. The **ospf** module reports an error when a device without the corresponding feature runs OSPF in a VRF with IPv4 or IPv6 addresses.
* **isis** -- The templates configure IS-IS instances in VRFs. The **isis** module reports an error when a device without this feature runs IS-IS in a VRF.
* **ripv2**, **ripng** -- The templates configure RIPv2 or RIPng instances in VRFs. The **ripv2** module reports an error when a device without the corresponding feature runs RIP in a VRF with IPv4 or IPv6 addresses.
* **bgp** -- The templates configure BGP neighbors in VRF BGP instances. The **bgp** module reports an error when a device without this feature has a BGP neighbor in a VRF. The VRF BGP address families (used to advertise VRF prefixes and to import routes from other VRFs) have to be configured on all devices that support VRFs and BGP.
* **leaking** -- Set this feature to **false** if your device (or your template) cannot implement inter-VRF route leaking (see [](dev-vrf-leaking)). The **vrf** module reports an error when a device without this feature uses a VRF with inter-VRF route leaking. Users can disable this check by setting **defaults.vrf.warnings.leaking** to **False**.
* **loopback** -- Set this feature to **false** if your device cannot have VRF loopback interfaces. The **vrf** module reports an error when a device without this feature needs a VRF loopback interface. Users can disable this check by setting **defaults.vrf.warnings.loopback** to **False**.
* **keep_module** -- Do not remove the **vrf** module from nodes that have no VRF interfaces or VRF loopbacks. Use this feature if your device needs the VRF configuration template for other purposes.
* **caveats.core**, **leaking_caveats**, **loopback_caveats**, **ospfv2_caveats**, **ospfv3_caveats**, **bgp_caveats**, **ripv2_caveats**, **ripng_caveats**, **isis_caveats** -- **true** or the anchor of the [caveats](platform-caveats) section describing the limitations of the VRF implementation or the specified VRF feature (used only to add caveat links to the [supported features tables](dev-features-tables))

The VRF loopback interface names are created from the **loopback_interface_name** device attribute (see [](dev-vrf-loopback)).

(dev-vrf-data)=
## VRF Parameters

VRFs used on a device are defined in the node **vrfs** dictionary. Dictionary keys are VRF names, dictionary values are dictionaries of VRF parameters:

* **id** (integer) -- The VRF ID
* **vrfidx** (integer) -- A unique VRF index (starting with 100). Use it when your device needs a numeric identifier for a VRF-specific object (for example, the OSPF process ID of a VRF OSPF instance).
* **rd** (string) -- The VRF route distinguisher
* **import** and **export** (list) -- The import and export route targets
* **af** (dictionary) -- The address families (**ipv4** and/or **ipv6**) used in the VRF. Use it to enable IPv4 and IPv6 routing in the VRF.
* **_leaked_routes** (boolean, optional) -- The VRF uses inter-VRF route leaking (see [](dev-vrf-leaking))
* **loopback_address** (dictionary, optional) -- The IPv4 and IPv6 addresses of the VRF loopback interface (see [](dev-vrf-loopback))
* **networks** (list, optional) -- The prefixes of the VRF loopback interfaces
* **ospf**, **isis**, **ripv2** (dictionary, optional) -- The parameters of the IGP instances running in the VRF (see [](dev-vrf-igp))
* **bgp** (dictionary, optional) -- The parameters of the VRF BGP instance (see [](dev-vrf-bgp))

The VRF interfaces (including VRF loopback interfaces) are in the node **interfaces** list and have the **vrf** interface parameter that contains the VRF name. The interfaces running an IGP in a VRF are also in the **vrfs._vrf-name_._igp_.interfaces** list.

(dev-vrf-loopback)=
## VRF Loopback Interfaces

The **vrf** module creates VRF loopback interfaces (see [VRF loopbacks](vrf-loopback)) and adds them to the node **interfaces** list. The VRF loopback interfaces have the **type** parameter set to **loopback** and the **vrf** parameter set to the VRF name. The **vrf** module also sets the **loopback_address** and **networks** VRF parameters.

The VRF loopback interface name is created from the **loopback_interface_name** device attribute. Use the `{ifindex}` placeholder to create unique interface names; the loopback interface number (shared with other additional loopback interfaces, starting with 1 or with the **loopback_offset** device attribute) is inserted in its place. For example, Cisco IOS uses:

```
loopback_interface_name: Loopback{ifindex}
```

When a VRF has a loopback interface, the VRF unnumbered IPv4 interfaces use the VRF loopback interface (not the global loopback interface) as their parent interface (**_parent_intf** and **_parent_ipv4** interface parameters).

(dev-vrf-principles)=
## VRF Configuration Principles

Many network devices lose interface IP addresses when you configure a VRF on the interface. Interface VRF membership should therefore be configured before interface IP addresses -- in the **initial** phase of device configuration.

In most cases, you have to create VRFs before you can use them in interface configuration. The best way to configure VRFs is thus:

* Create VRFs in `netsim/ansible/templates/initial/<nos>.vrf.j2` template.
* Invoke that template in `netsim/ansible/templates/initial/<nos>.j2` template whenever the device data contains **vrfs** dictionary.
* Configure interface VRF membership as part of the standard interface configuration
* Configure VRF routing protocols (OSPF, IS-IS, RIP, BGP) in `netsim/ansible/templates/vrf/<nos>.j2` template

## Create VRFs

In the _create VRF_ template (stored in `netsim/ansible/templates/initial/<nos>.vrf.j2`) iterate over the **vrfs** dictionary and configure VRFs.

Cisco IOS configures most VRF parameters (RD, RT) in the VRF definition, and uses address families within VRF definition to enable IPv4 and/or IPv6 in the VRF:

```jinja
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
{%   for af in ['ipv4','ipv6'] if af in vdata.af|default({}) %}
 address-family {{ af }}
 exit-address-family
!
{%   endfor %}
{% endfor %}
```

Other devices might configure only the route distinguisher in the VRF definition (Arista EOS configures route targets in the VRF BGP instance), or might have to enable IPv4 and IPv6 routing in individual VRFs.

Include the VRF creation template in `netsim/ansible/templates/initial/<nos>.j2` template:

```jinja
{% if vrfs is defined %}
{% include '<nos>.vrf.j2' %}
{% endif %}
```

Finally, put interfaces into VRFs based on **vrf** interface parameter within the interface configuration part of `netsim/ansible/templates/initial/<nos>.j2`. For example:

```jinja
{% for l in interfaces|default([]) %}
interface {{ l.ifname }}
 no shutdown
{% if l.vrf is defined %}
 vrf forwarding {{ l.vrf }}
{% endif %}
...
{% endfor +%}
```

(dev-vrf-routing)=
## Configuring VRF Routing Protocols

Configure the VRF routing protocols in the `netsim/ansible/templates/vrf/<nos>.j2` template. Implement the routing protocol configuration as macros shared between the global and VRF configuration templates to ensure feature parity between global and VRF routing protocol instances (see [](dev-ospf-macro), [](dev-isis-vrf), and [](dev-rip-vrf)), and include a separate template to configure the VRF BGP instances when the device runs BGP (**bgp.as** is defined).

This is how the Cisco IOS VRF template configures the VRF routing protocols:

```jinja
{% import "templates/ospf/ios.ospfv2.j2" as ospfv2 with context %}
{% import "templates/ospf/ios.ospfv3.j2" as ospfv3 with context %}
{% import "templates/ripv2/ios.macro.j2" as rip with context %}
{% if bgp.as is defined %}
{% include 'ios.bgp.j2' +%}
{% endif %}
!
{% for vname,vdata in vrfs.items() if 'ospf' in vdata %}
{%   if vdata.af.ipv4|default(False) %}
{{     ospfv2.config(vdata.vrfidx,vname,vdata.ospf,vdata.ospf.interfaces|default([]),bgp|default({})) }}
{%   endif %}
{%   if vdata.af.ipv6|default(False) %}
{{     ospfv3.config(vdata.vrfidx,vname,vdata.ospf,vdata.ospf.interfaces|default([]),bgp|default({})) }}
{%   endif %}
{% endfor %}
!
{% for vname,vdata in vrfs.items() if 'ripv2' in vdata %}
{{   rip.config(ripv2=vdata.ripv2,vrf=vname,ospf_pid=vdata.vrfidx) }}
{% endfor %}
```

(dev-vrf-igp)=
### VRF IGP Instances

The parameters of an IGP instance running in a VRF (**vrfs._vrf-name_.ospf**, **vrfs._vrf-name_.isis**, or **vrfs._vrf-name_.ripv2** dictionary) are (mostly) identical to the global IGP parameters. The differences are:

* **interfaces** (list) -- The VRF interfaces on which the device should run the IGP. Use this list instead of the node **interfaces** list.
* **active** (boolean) -- The VRF IGP instance is active
* **router_id** (string) -- The VRF OSPF router ID (it is always defined)
* **import** (dictionary) -- The routing protocols to redistribute into the VRF IGP. When the user does not specify the VRF route import, _netlab_ creates a default import dictionary (for example, BGP and connected routes are redistributed into the VRF OSPF instance on devices running BGP). The default import entries have the **auto** parameter set to **true**.

Use the **vrfidx** VRF parameter when your device needs a numeric routing process ID (for example, the OSPF process ID), and the global parameters that are not VRF-specific (for example, **ospf.reference_bandwidth**).

(dev-vrf-bgp)=
### VRF BGP Instances

In the VRF BGP configuration template, configure VRF address families, route redistribution, advertise VRF-specific networks, and configure VRF BGP neighbors. Use attributes defined in the [](dev-config-bgp) document; many of them (for example, **bgp.advertise**, **bgp.import**, and **bgp.neighbors**) are available in the VRF **bgp** data ([more details](dev-bgp-vrf)).

```{warning}
Some devices don't inherit the VRF BGP router ID from the global router ID and may fail to function correctly in IPv6-only deployments.

As the VRF BGP router ID is not always defined, use the `vdata.bgp.router_id|default(bgp.router_id)` expression when you have to configure a VRF BGP router ID.
```

To configure VRF BGP neighbors, use the BGP neighbor configuration macro from the global BGP configuration template (if it exists for your platform) to ensure feature parity between global and VRF BGP neighbors.

This is how the Cisco IOS VRF BGP template configures VRF address families, route redistribution, prefix advertisements, and VRF BGP neighbors:

```jinja
{% import "templates/bgp/ios.macro.j2" as bgpcfg %}
{% import "templates/routing/_redistribute.ios.j2" as redistribute with context %}
!
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
{%   for af in ('ipv4','ipv6') if af in vdata.af|default({}) %}
!
 address-family {{ af }} vrf {{ vname }}
  bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{%     if vdata.bgp.import is defined %}
{{       redistribute.config(vdata.bgp,af=af,ospf_pid=vdata.vrfidx,vrf=vname)|indent(1,first=True) }}
{%     endif %}
!
{%     for n in vdata.bgp.advertise|default([]) if af in n %}
{{       bgpcfg.bgp_network(af,n[af]) }}
{%     endfor %}
!
{%     for n in vdata.bgp.neighbors|default([]) if af in n %}
{{       bgpcfg.neighbor_global(n,n[af]) }}
{{       bgpcfg.neighbor_af(n,n[af],bgp) }}
{%     endfor %}
 exit-address-family
{%   endfor %}
{% endfor %}
```

Some devices (for example, Arista EOS) configure the VRF route distinguisher and route targets in the VRF BGP instance; they might also need separate IPv4 and IPv6 route targets.

(dev-vrf-leaking)=
## Inter-VRF Route Leaking

A VRF uses inter-VRF route leaking when its import or export route targets differ from its route distinguisher. The **vrf** module sets the **_leaked_routes** VRF parameter on such VRFs.

Most devices implement inter-VRF route leaking with BGP (for example, with VPNv4/VPNv6 address families or VRF BGP instances importing and exporting route targets). The **vrf** module copies the **vrf.as** node parameter into **bgp.as** when a node uses inter-VRF route leaking but does not run BGP, and reports an error when neither of them is defined. Use the **_leaked_routes** VRF parameter if your device needs extra configuration (for example, a VRF BGP instance) only when the VRF uses inter-VRF route leaking.

## Integration Tests

The VRF integration tests are in the `tests/integration/vrf` directory:

* `01-multi-vrf.yml` to `04-multi-vrf-loopback-ipv6.yml` -- Basic VRF-lite functionality (IPv4, IPv6, VRF loopbacks)
* `11-multi-vrf-ospf.yml` to `16-vrf-bgp-community.yml` -- OSPF and BGP in VRFs, unnumbered VRF interfaces, VRF BGP communities
* `21-multi-vrf-ospfv3.yml` to `23-multi-vrf-mixed-ipv6.yml` -- OSPFv3 and IPv6 BGP in VRFs
* `31-vrf-common-hosts.yml` to `35-vrf-asymmetric-leaking.yml` -- Inter-VRF route leaking (common services VRF, asymmetric route leaking)

The IGP-specific VRF tests are in the IGP integration test directories (for example, `tests/integration/isis/30-vrf.yml`).
