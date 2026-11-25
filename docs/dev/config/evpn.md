(dev-config-evpn)=
# Configuring EVPN

This document describes the device data model parameters used in EVPN device configuration templates. Please see the [contributing new devices](dev-new-devices) document for a wider picture.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/ansible/templates/evpn/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](dev-devices-ansible-vars) for more details).
* The EVPN configuration is applied after the VLAN, VXLAN, and VRF configuration. The EVPN template has to configure only the EVPN address family on BGP sessions, the MAC-VRF (VLAN) and IP-VRF EVPN instances, and the symmetric IRB transit VNIs.
* The VXLAN VNIs (**vni** VLAN attribute) and the list of VXLAN-enabled VLANs and VRFs (**vxlan.vlans** and **vxlan.l3vnis** node attributes) are set by the [**vxlan** module](module-vxlan) and should be configured in the VXLAN template.
* The nodes without VLANs or VRFs (for example, EVPN route reflectors) have no **vlans** or **vrfs** dictionaries. Use `vlans|default({})` or `vrfs|default({})` in your loops (as in the examples below), or put the whole loop inside an `{% if vlans is defined %}` or `{% if vrfs is defined %}` block.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-evpn-features)=
## Device Features

You can use the following **features.evpn** [device features](dev-device-features) to specify which EVPN features your configuration template implements:

* **transport** -- The list of EVPN transport (data plane) encapsulations (**vxlan**, **mpls**, **sr**) the device implements.
* **bgp_session** -- A dictionary of EVPN transports the device supports in the control plane. The dictionary values are the lists of BGP session types (**ibgp**, **ebgp**) that can carry the EVPN address family for that transport. For example:

  ```yaml
  evpn:
    transport: [ mpls, sr ]
    bgp_session: { mpls: [ ibgp ], sr: [ ibgp ], vxlan: [ ibgp ] }
  ```

  The **evpn** module reports an error when:

  * A node uses an **evpn.transport** that is not in the device **bgp_session** dictionary.
  * A node has an EVPN-enabled BGP session of a type not listed for the node's transport.
  * A control-plane-only node (the transport is in the **bgp_session** dictionary but not in the **transport** list; for example, a route reflector) has EVPN-enabled VLANs or VRFs.

  An empty **transport** list (or no **transport** feature) thus describes a control-plane-only device.

* **irb** -- The template configures symmetric IRB with VXLAN transport (VRFs with **evpn.transit_vni**). The **evpn** module reports an error when a device without this feature uses a VRF with a transit VNI. _netlab_ always uses symmetric IRB with MPLS transport; this feature is not checked for MPLS-based EVPN.
* **asymmetrical_irb** -- The template configures asymmetric IRB with VXLAN transport (VRFs without **evpn.transit_vni**). The **evpn** module reports an error when a device without this feature uses a VRF with IPv4 or IPv6 addresses but without a transit VNI with VXLAN transport.
* **bundle** -- The list of supported VLAN bundle services. _netlab_ implements only the **vlan_aware** bundle service. The **evpn** module reports an error when a VRF uses an unsupported **evpn.bundle** value.
* **multi_rt** -- The template configures multiple import or export route targets in MAC-VRF (VLAN) EVPN instances. The **evpn** module reports an error when a device without this feature has more than one VLAN **evpn.import** or **evpn.export** value.
* **ipv6** -- The device can run EVPN with IPv6 next hops (EVPN over IPv6 BGP sessions used with VXLAN-over-IPv6 transport). The **evpn** module reports an error when a device without this feature uses IPv6 VTEPs.
* **multihoming.lag**, **multihoming.interface**, **multihoming.esi_auto** -- The device supports Ethernet segments on LAG interfaces (ESI-LAG), Ethernet segments on other interfaces, and automatic ESI values based on the LACP system ID. These features are checked by the [**evpn.multihoming** plugin](plugin-evpn-multihoming); the **lag** module also allows a device with the **multihoming.lag** feature to be on the M-side of a LAG when the lab topology uses that plugin.
* **caveats.core**, **caveats.irb**, **caveats.mpls_irb**, **caveats.ebgp** -- **true** or the anchor of the [caveats](platform-caveats) section describing the limitations of the EVPN/VXLAN implementation, VXLAN symmetric IRB, MPLS symmetric IRB, or EBGP-based EVPN (used only to add caveat links to the [supported features tables](dev-features-tables))

(dev-evpn-node)=
## Node Parameters

The **evpn** module sets these parameters in the node **evpn** dictionary:

* **transport** (string) -- The EVPN transport: **vxlan** or **mpls** (the **evpn** module changes the **sr** transport into **mpls** as they're identical from the EVPN perspective)
* **session** (list) -- The BGP session types (**ibgp**, **ebgp**) on which the EVPN address family should be enabled. Use the **evpn** BGP neighbor attribute (see below) to configure individual BGP neighbors.
* **vlans** (list) -- The EVPN-enabled VLANs present on the node
* **vrfs** (list) -- The EVPN-enabled VRFs (IP-VRF EVPN instances) present on the node

(dev-evpn-neighbors)=
### BGP Neighbors

The **evpn** module sets the **evpn** attribute of the BGP neighbors (**bgp.neighbors** list) with which the node should exchange EVPN routes. Its value is the address family (**ipv4** or **ipv6**) of the BGP session that should carry the EVPN address family. Use the **local_if** neighbor attribute (when present) to configure unnumbered BGP sessions.

This is how the Arista EOS template activates the EVPN address family:

```jinja
router bgp {{ bgp.as }}
 address-family evpn
{% for n in bgp.neighbors if n.evpn|default(False) %}
{%   set peer = 'ebgp_intf_' + n.local_if if n.local_if is defined else n[n.evpn] %}
  neighbor {{ peer }} activate
{% endfor %}
```

(dev-evpn-vlan)=
## VLAN Parameters

The **evpn** module sets these parameters in the **evpn** dictionary of EVPN-enabled node VLANs (node **vlans** dictionary):

* **evi** (integer) -- The EVPN instance identifier (default: VLAN ID)
* **rd** (string) -- The route distinguisher (default: _router-id_:_evi_)
* **import** and **export** (list) -- The import/export route targets (default: _asn_:_evi_). These attributes are not set on VLANs that are part of a VLAN bundle.
* **bundle** (string) -- The VLAN bundle service type. The VLANs with this parameter are part of a VLAN bundle defined in their VRF; they should not be configured as individual MAC-VRF instances.

This is how the Arista EOS template configures VLAN-based EVPN services:

```jinja
{% for v in (vlans|default({})).values() if v.evpn.evi is defined and v.evpn.bundle is not defined %}
 vlan {{ v.id }}
  rd {{ v.evpn.rd }}
{%   for irt in v.evpn.import|default([]) %}
  route-target import {{ irt }}
{%   endfor %}
{%   for ert in v.evpn.export|default([]) %}
  route-target export {{ ert }}
{%   endfor %}
  redistribute learned
{% endfor %}
```

(dev-evpn-vrf)=
## VRF Parameters

The **evpn** module sets these parameters in the **evpn** dictionary of EVPN-enabled node VRFs (node **vrfs** dictionary):

* **evi** (integer) -- The EVPN instance identifier (default: VRF ID plus 5000 for VRFs listed in the global **evpn.vrfs** list, VRF ID otherwise)
* **rd** (string) -- The EVPN route distinguisher (default: _router-id_:_evi_). Most templates use the VRF route distinguisher (**rd** VRF attribute) and the VRF import/export route targets (**import** and **export** VRF attributes) set by the [**vrf** module](module-vrf) instead.
* **transit_vni** (integer) -- The transit VNI used for VXLAN symmetric IRB. A VRF without this parameter uses asymmetric IRB with VXLAN transport.
* **bundle** (string) -- The VLAN bundle service type (currently always **vlan_aware**)
* **vlans** and **vlan_ids** (list) -- The names and IDs of the EVPN-enabled VLANs in the VLAN bundle

Use the **af** VRF attribute to check whether the VRF needs an IP-VRF EVPN instance (VRFs that are used only to define VLAN bundles have no IPv4 or IPv6 addresses).

This is how the Arista EOS template configures the IP-VRF EVPN instances and the symmetric IRB transit VNIs:

```jinja
{% for n,v in vrfs|default({})|dictsort if v.af is defined %}
 vrf {{ n }}
  rd {{ v.rd }}
{%   for irt in v.import|default([]) %}
  route-target import evpn {{ irt }}
{%   endfor %}
{%   for ert in v.export|default([]) %}
  route-target export evpn {{ ert }}
{%   endfor %}
  redistribute connected
{% endfor %}
{% for n,v in vrfs|default({})|dictsort if v.evpn.transit_vni is defined %}
{%   if loop.first %}
!
interface vxlan 1
{%   endif %}
 vxlan vrf {{ n }} vni {{ v.evpn.transit_vni }}
{% endfor %}
```

## Integration Tests

The EVPN integration tests are in the `tests/integration/evpn` directory:

* `01-vxlan-bridging.yml` to `06-vxlan-bridging-vlan-bundle.yml` -- VXLAN bridging, asymmetric and symmetric IRB, central routing, layer-3-only EVPN, and VLAN bundle service
* `10-vxlan-rr.yml` -- EVPN route reflector (use this test for control-plane-only devices)
* `11-vxlan-ebgp.yml` to `15-vxlan-ebgp-unnumbered.yml` -- IBGP/EBGP designs (including unnumbered EBGP sessions)
* `20-vxlan-irb-ospf.yml` to `22-ospf-ce-router.yml` -- Routing protocols in EVPN VRFs
* `30-cs-bridging.yml` -- Multiple import/export route targets (E-Tree service)
* `41-vxlan-ipv6-bridging.yml` -- VXLAN over IPv6 (EVPN with IPv6 next hops)
* `51-mpls-bridging.yml` to `54-evpn-l3vpn.yml` -- EVPN with MPLS transport
* `61-sr-bridging.yml` -- EVPN with SR-MPLS transport

The EVPN multihoming tests are in the `tests/integration/evpn.multihoming` directory.
