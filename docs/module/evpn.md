# Ethernet Virtual Private Network (evpn) Configuration Module

This configuration module configures the BGP EVPN address family on Nokia SR OS, Nokia SR Linux, Arista EOS and FRR. The module depends on the BGP module.

The current implementation of EVPN module supports:

* VXLAN-based transport over IPv4
* VLAN-Based Service (bridging of a single VLAN within an EVPN Instance)
* VLAN-Aware Bundle Service (bridging of multiple related VLANs inside a single EVPN Instance)
* Symmetric IRB

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual VXLAN features:

| Operating system   | VXLAN<br>transport | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ✅  |  ❌  | ✅  |
| Nokia SR Linux     | ✅  | ✅  |  ❌  |  ❌  |  ❌  |
| Nokia SR OS        |  ❌  |  ❌  |  ❌  |  ❌  |  ❌  |
| FRR                |  ❌  |  ❌  |  ❌  |  ❌  |  ❌  |
| VyOS               |  ✅  |  ✅  |  ❌  |  ❌  |  ❌  |

EVPN module supports three design paradigms:

* IBGP with IGP (default on non-Nokia devices)
* IBGP over EBGP (default on Nokia devices)
* EBGP-only (requires manual configuration of RD/RT values on most platforms)

| Operating system   | IBGP+IGP | EBGP-only | EBGP over<br>IBGP | IPv4<br>transport | IPv6<br>transport |
| ------------------ | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  |  ❌  | ✅  |  ❌  |
| Nokia SR Linux     |  ❌  | ✅  | ✅  | ✅  | ✅  |
| Nokia SR OS        |  ❌  | ✅  | ✅  | ✅  | ✅  |
| FRR                | ✅  | ✅  | ✅  | ✅  | ✅  |
| VyOS               | ✅  | ✅  | ❌  | ✅  | ❌  |

**Notes:**
* FRR implementation is a control-plane-only implementation that can be used as a route reflector. It enables EVPN over IPv4 and/or IPv6 on configured type(s) of BGP sessions. It's expected that the other end of the session won't negotiate EVPN or IPv4 AF.
* While VyOS itself supports IPv6 transport for VXLAN, using static flooding with the **vxlan** module, this seems not working with EVPN, where an IPv4 VTEP is always announced by **frr**.

## Parameters

EVPN module supports these default/global/node parameters:

* **evpn.session** (global or node parameter): A list of BGP session types on which the EVPN address family is enabled (default: `ibgp`)
* **evpn.start_transit_vni** (system default parameter) -- the first symmetric IRB transit VNI

### VLAN-Based Service Parameters

EVPN-related VLAN parameters are set on **vlans** dictionary. You can set the following parameters for every VLAN using VLAN-Based Service:

* **evpn.evi**: EVPN Instance identifier.
* **evpn.rd**: EVPN Instance route distinguisher (not checked at the moment). Default: 
* **evpn.import** and **evpn.export**: Import and export route targets (not checked at the moment).

EVPN configuration module sets the following default EVI/RD/RT values for [VXLAN-enabled VLANs](vxlan.md#selecting-vxlan-enabled-vlans):

* **evpn.evi**: `vlan-id`
* **evpn.rd**: `router-id:vlan-id` (according to Section 7.9 of RFC 7432)
* **evpn.import** and **evpn.export**: `bgp-as:vlan-id` (according to Section 7.10 of RFC 7432 and Section 5.1.2.1 of RFC 8365)

### VLAN-Aware Bundle Service

VLAN-Aware Bundle Service uses VRF configuration (and thus requires [VRF configuration module](vrf.md)). All VLANs belonging to a single VRF are configured as a VLAN bundle. [RD and RT values assigned by VRF module](vrf.md#rd-and-rt-values) are used to configure the VLAN bundle; you can set **evpn.evi** VRF parameter to set the EVPN Instance identifier.

The default value of VRF EVPN Instance identifier is the VLAN ID of the first VLAN in that VRF.

### Integrated Routing and Bridging

IRB is configured whenever EVPN-enabled VLANs in a VRF contain IPv4 or IPv6 addresses:

* Asymmetric IRB requires no extra parameters[^NS]
* Symmetric IRB needs a transit VNI that has to be set with the **evpn.transit_vni** parameter. That parameter could be set to an integer value or to *True* in which case the EVPN configuration module assigns a VNI to the VRF.

[^NS]: Asymmetric IRB is not supported at the moment
