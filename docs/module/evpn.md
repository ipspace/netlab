# Ethernet Virtual Private Network (evpn) Configuration Module

This configuration module configures the BGP EVPN address family on Nokia SR OS, Nokia SR Linux, Arista EOS and FRR. The module depends on the BGP module.

The current implementation of EVPN module supports:

* VXLAN-based transport
* VLAN-Based Service (bridging of a single VLAN within an EVPN Instance)
* VLAN-Aware Bundle Service (bridging of multiple related VLANs inside a single EVPN Instance)

The EVI (EVPN Instance) value can be set with **evpn.evi** VLAN attribute, RD and RT values (when missing) are computed from EVI or VLAN ID using the rules from Section 7.9 and 7.10 of RFC 7432.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual VXLAN features:

| Operating system   | VXLAN<br>transport | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ✅  |  ❌  |  ❌  |
| Nokia SR Linux     | ✅  | ✅  |  ❌  |  ❌  |  ❌  |
| Nokia SR OS        |  ❌  |  ❌  |  ❌  |  ❌  |  ❌  |
| FRR                |  ❌  |  ❌  |  ❌  |  ❌  |  ❌  |
| VyOS               |  ✅  |  ✅  |  ❌  |  ❌  |  ❌  |

EVPN module supports three design paradigms:

* IBGP with IGP (default on non-Nokia devices)
* IBGP over EBGP (default on Nokia devices)
* EBGP-only (requires manual configuration of RD/RT values on most platforms)

| Operating system   | IBGP+IGP | EBGP-only | EBGP over<br>IBGP | IPv4<br>transport | IPv6<br>transport |
| ------------------ | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  |  ❌  | ✅  |  ❌  |
| Nokia SR Linux     |  ❌  | ✅  | ✅  | ✅  | ✅  |
| Nokia SR OS        |  ❌  | ✅  | ✅  | ✅  | ✅  |
| FRR                | ✅  | ✅  | ✅  | ✅  | ✅  |
| VyOS               | ✅  | ✅  | ✅  | ✅  | ✅  |

**Notes:**
* FRR implement is a control-plane-only implementation that can be used as a route reflector. It enables EVPN over IPv4 and/or IPv6 on configured type(s) of BGP sessions. It's expected that the other end of the session won't negotiate EVPN or IPv4 AF.

## Parameters

EVPN module supports these global/node parameters:

* **evpn.session**: A list of BGP session types on which the EVPN address family is enabled (default: `ibgp`)
* **evpn.use_ibgp**: Nokia-only parameter that selects IBGP-over-EBGP (when set to `true`, default behavior) or EBGP-only (when set to `false`) design. Setting this parameter on Nokia devices also disables IBGP IPv4/IPv6 address family.

Other EVPN-related parameters are set on **vlans** dictionary. You can set the following parameters for every VLAN using VLAN-Based Service:

* **evpn.evi**: EVPN Instance identifier. Default: `vlan-id`.
* **evpn.rd**: EVPN Instance route distinguisher (not checked at the moment). Default: `router-id:vlan-id`
* **evpn.import** and **evpn.export**: Import and export route targets (not checked at the moment). Default: `bgp-as:vlan-id`

The default EVI/RD/RT values are set for [VXLAN-enabled VLANs](vxlan.md#selecting-vxlan-enabled-vlans).

VLAN-Aware Bundle Service uses VRF configuration (and thus requires [VRF configuration module](vrf.md)). All VLANs belonging to a single VRF are configured as a VLAN bundle. [RD and RT values assigned by VRF module](vrf.md#rd-and-rt-values) are used to configure the VLAN bundle; you can set **evpn.evi** VRF parameter to set the EVPN Instance identifier. The default value of VRF EVPN Instance identifier is the VLAN ID of the first VLAN in that VRF.
