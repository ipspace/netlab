(dev-config-isis)=
# Configuring IS-IS

This document describes the device data model parameters used in IS-IS device configuration templates. Please see the [contributing new devices](dev-new-devices) document for a wider picture.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/ansible/templates/isis/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](dev-devices-ansible-vars) for more details).
* The IS-IS configuration is applied after the VLAN and routing configuration. The VRF IS-IS instances are configured in the VRF template (see [](dev-isis-vrf)).
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)`, or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-isis-features)=
## Device Features

You can use the following **features.isis** [device features](dev-device-features) to specify which IS-IS features your configuration template implements:

* **unnumbered.ipv4**, **unnumbered.ipv6** -- IS-IS runs over unnumbered IPv4 interfaces or LLA-only IPv6 interfaces. The **isis** module reports an error when a device without these features runs IS-IS over such an interface.
* **unnumbered.network** -- IS-IS runs over unnumbered IPv4 multi-access links. The **isis** module reports an error when a device without this feature runs IS-IS over an unnumbered link with more than one neighbor.
* **import** -- The list of routing protocols that can be redistributed into IS-IS (add `vrf` to the list if you implemented the redistribution in VRFs)
* **circuit_type** -- The template configures IS-IS circuit type (**isis.type** interface attribute). The **isis** module warns the user when a device without this feature uses that attribute.
* **mt** -- Set this feature to **false** if your device (or your template) cannot run multi-topology IS-IS (see [](dev-isis-af)). The **isis** module reports an error (that can be disabled with the **defaults.isis.warnings.mt** setting) when such a device runs IS-IS with IPv6. A device without this feature is assumed to support multi-topology IS-IS.
* **caveats**, **unnumbered.caveats** -- **true** or the anchor of the [caveats](platform-caveats) section describing the limitations of the IS-IS implementation or IS-IS over unnumbered interfaces (used only to add caveat links to the [supported features tables](dev-features-tables))

IS-IS in VRFs is controlled by the **vrf.isis** feature.

(dev-isis-af)=
## Supporting Multiple Address Families

The **isis.af** variable contains a dictionary of address families configured on the device. It is present in node and VRF data structures.

* **isis.af.ipv4** -- there is at least one interface on which you could run IS-IS for IPv4
* **isis.af.ipv6** -- there is at least one interface on which you could run IS-IS for IPv6

_netlab_ configures IPv6 IS-IS as multi-topology IS-IS (RFC 5120). Devices running single-topology IS-IS cannot exchange IPv6 routes with devices running multi-topology IS-IS; if your device cannot run multi-topology IS-IS, set the **features.isis.mt** to **false**.

This is how the FRR template enables IPv6 forwarding and multi-topology IS-IS:

```jinja
{% if 'ipv6' in isis.af %}
ipv6 forwarding
{% endif %}
!
router isis {{ isis.instance }}{% if vrf %} vrf {{ vrf }}{% endif +%}
 is-type {{ isis.type }}
 metric-style wide
 net {{ isis.net }}
{% if isis.af.ipv6 is defined %}
 topology ipv6-unicast
{% endif %}
```

(dev-isis-node)=
## Node Parameters

The **isis** module sets these parameters in the node **isis** dictionary:

* **instance** (string) -- The IS-IS instance (process) name
* **net** (string) -- The NSAP address (NET) of the node. Use it to configure the IS-IS NET.
* **area** and **system_id** (string) -- The IS-IS area and system ID (the parts of the NET). Use them if your device cannot configure the NET directly.
* **type** (string) -- The IS-IS router type (**level-1**, **level-2**, or **level-1-2**)
* **af** (dictionary) -- The IS-IS address families (see [](dev-isis-af))
* **import** (dictionary) -- The routing protocols to redistribute into IS-IS. The dictionary keys are the protocol names (for example, **connected** or **ospf**); the values are dictionaries that might contain the **policy** attribute (the name of the routing policy to apply to the redistributed routes). Most templates use the `templates/routing/_redistribute.<nos>.j2` macros to configure the route redistribution.
* **bfd** (dictionary, optional) -- The address families in which IS-IS uses BFD. Use the interface **isis.bfd** attribute if your device can enable BFD on individual interfaces.

(dev-isis-intf)=
## Interface Parameters

The **isis** module sets the **isis** dictionary on all interfaces on which the device should run IS-IS, including the loopback interface. Interfaces without the **isis** dictionary (layer-2 interfaces, external interfaces, VRF interfaces in the node **interfaces** list) should not be configured. Use **netlab_interfaces** (a list containing the loopback interface and the node **interfaces**) to configure the loopback and the physical interfaces in a single loop.

The **isis** interface dictionary contains these parameters:

* **passive** (boolean) -- The interface should be a passive IS-IS interface. This parameter is always present; stub interfaces and interfaces with the **isis.passive** link attribute are passive.
* **network_type** (string, optional) -- The IS-IS network type. Its only value is **point-to-point**; it is set on point-to-point links and on the interfaces with the **isis.network_type** attribute. Interfaces without this parameter use the default (broadcast) network type.
* **type** (string, optional) -- The IS-IS circuit type (**level-1**, **level-2**, or **level-1-2**). Implement it only if your device has the **features.isis.circuit_type** feature.
* **metric** (integer, optional) -- The interface metric (the **isis.cost** link attribute is normalized into this parameter)
* **bfd** (dictionary, optional) -- The address families in which IS-IS should use BFD on this interface. The IGP BFD state is calculated by the transformation code; see [IGP/BFD interaction](dev-config-bfd) for more details.

Configure IS-IS for an address family on an interface only when the interface has an address from that address family (**ipv4** or **ipv6** interface attribute) and the address family is in the **isis.af** dictionary. The **ipv4** attribute of an unnumbered IPv4 interface and the **ipv6** attribute of an LLA-only IPv6 interface are set to **true**.

This is how the FRR template configures IS-IS interfaces:

```jinja
{% for l in interfaces|default([]) if 'isis' in l %}
interface {{ l.ifname }}
{%   if 'ipv4' in l and 'ipv4' in isis.af %}
 ip router isis {{ isis.instance }}
{%   endif %}
{%   if 'ipv6' in l and 'ipv6' in isis.af  %}
 ipv6 router isis {{ isis.instance }}
{%   endif %}
{%   if l.isis.network_type is defined %}
 isis network {{ l.isis.network_type }}
{%   endif %}
{%   if l.isis.type is defined %}
 isis circuit-type {{ l.isis.type }}
{%   endif %}
{%   if l.isis.metric is defined %}
 isis metric {{ l.isis.metric }}
{%   endif %}
{%   if l.isis.passive %}
 isis passive
{%   endif %}
{%   if l.isis.bfd is defined %}
 isis bfd
{%   endif %}
{% endfor %}
```

(dev-isis-vrf)=
## VRF IS-IS Instances

The VRFs in which the device should run IS-IS have an **isis** dictionary that contains the same parameters as the node **isis** dictionary (see [](dev-isis-node)) plus:

* **interfaces** (list) -- The VRF interfaces on which the device should run IS-IS. These interfaces have the same **isis** parameters as the global interfaces (see [](dev-isis-intf)).
* **active** (boolean) -- The VRF IS-IS instance is active

The **instance** parameter of a VRF IS-IS instance is set to the VRF name.

The VRF IS-IS instances are configured in the VRF configuration template (`netsim/ansible/templates/vrf/<nos>.j2`). To avoid duplicating the IS-IS configuration code, implement the IS-IS configuration as a macro (stored in `netsim/ansible/templates/isis/<nos>.macro.j2`) that takes the IS-IS data, the list of interfaces, and the VRF name as parameters, and call that macro from the IS-IS and VRF templates.

This is how the FRR IS-IS template calls the IS-IS configuration macro:

```jinja
{% import "frr.macro.j2" as isis_config with context %}
{% if isis is defined %}
{{ isis_config.config(isis,netlab_interfaces) }}
{% endif %}
```

This is how the FRR VRF template calls the same macro to configure VRF IS-IS instances:

```jinja
{% import "templates/isis/frr.macro.j2" as isis_config with context %}
{% for vname,vdata in vrfs.items() if vdata.isis is defined %}
{{   isis_config.config(vdata.isis,vdata.isis.interfaces,vname) }}
{% endfor %}
```

## Integration Tests

The IS-IS integration tests are in the `tests/integration/isis` directory:

* `01-ipv4.yml` to `03-dual-stack.yml` -- IS-IS with IPv4, IPv6, and dual-stack addressing (level-1 and level-2 routers)
* `10-network.yml` -- IS-IS network types
* `11-cost.yml` -- IS-IS interface metrics
* `12-passive.yml` -- Passive IS-IS interfaces
* `21-import-ds.yml` -- Route redistribution between IS-IS, OSPFv2/OSPFv3, and BGP
* `30-vrf.yml` -- VRF IS-IS instances

The `tests/integration/sr` and `tests/integration/srv6` directories contain the SR-MPLS and SRv6 tests that use IS-IS.
