# Ethernet Virtual Private Network (evpn) Configuration Module

This configuration module configures the BGP EVPN address family on Nokia SR OS, Nokia SR Linux, Arista EOS and FRR. The module depends on the BGP module.

The current implementation of EVPN module supports:

* VXLAN-based transport over IPv4 and MPLS-based transport
* VLAN-Based Service (bridging of a single VLAN within an EVPN Instance)
* VLAN-Aware Bundle Service (bridging of multiple related VLANs inside a single EVPN Instance)
* Symmetric and asymmetric IRB

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual EVPN/VXLAN features:

| Operating system   | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX       | ✅  |  ❌  |  ✅  | ✅[❗](caveats-aruba)  |
| Cisco Nexus OS     | ✅  |  ❌  |  ❌  | ✅  |
| Cumulus Linux      | ✅  |  ❌  | ✅  | ✅  |
| Dell OS 10         | ✅  |  ❌  |  ✅  | ✅  |
| FRR                | ✅  |  ❌  |  ❌  | ✅  |
| Nokia SR Linux     | ✅  |  ✅ | ✅  | ✅  |
| Nokia SR OS        | ✅  |  ❌  | ✅  | ✅  |
| VyOS               | ✅  |  ❌  |  ✅  | ✅  |

The following table describes per-platform support of individual EVPN/MPLS features:

| Operating system   | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  |  ❌  |  ❌  |

```{note}
* Arista EOS requires anycast gateway for EVPN/MPLS symmetric IRB configuration.
```

Devices supporting [EVPN VLAN bundle services](evpn-bundle-service) implement the following bundle service types (see RFC 7432 section 6 for more details):

| Operating system   | VLAN<br>bundle | Port<br>service | VLAN-aware<br>bundle | Port-based<br>VLAN bundle |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         |  ❌  |  ❌  | ✅  |  ❌  |
| Nokia SR Linux     |  ❌  |  ❌  | ✅  |  ❌  |

EVPN module supports three design paradigms:

* IBGP with IGP
* IBGP over EBGP
* EBGP-only (requires manual configuration of RD/RT values on most platforms)

| Operating system   | IBGP+IGP | BGP RR | EBGP-only | IBGP over<br>EBGP | IPv4 BGP<br>transport | IPv6 BGP<br>transport |
| ------------------ | :-: | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ❌   | ❌   | ✅  | ❌   |
| Aruba AOS-CX       | ✅  | ✅  | ✅  | ✅  | ✅  | ❌   |
| Cisco Nexus OS     | ✅  | ✅  | ❌   | ❌   | ✅  | ❌   |
| Cumulus Linux      | ✅  | ✅  | ❌   | ❌   | ✅  | ❌   |
| Dell OS 10         | ✅  | ✅  | ✅  | ✅  | ✅  | ❌   |
| FRR                | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  |
| Nokia SR Linux     | ✅  | ✅  |  ❌  | ✅  | ✅  | ✅  |
| Nokia SR OS        | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  |
| VyOS               | ✅  | ✅  | ✅  | ✅  | ✅  | ❌   |

```{note}
* Nokia SR Linux supports iBGP EVPN sessions over BGP unnumbered with IPv6 link-local addresses, using IPv4 VXLAN routes with IPv6 next hops
* While VyOS itself supports IPv6 transport for VXLAN, using static flooding with the **vxlan** module, this seems not working with EVPN, where an IPv4 VTEP is always announced by **frr**.
* Dell OS10 only allows to configure the EVPN RD in the form `X.X.X.X:N`. By default, *netlab* uses `N:M` for L3VNI, so on this platform the L3VNI RD is derived from the Router-ID and the VRF ID as `router-id:vrf-id` (and the one generated by *netlab* is not used).
```

(evpn-global-parameters)=
## Global EVPN Parameters

EVPN module supports these default/global/node parameters:

* **evpn.vrfs** (global or node parameter): A list of EVPN-enabled VRFs. Default value with VXLAN transport: all global VRFs with **evpn.transit_vni** parameter. There is no default value with MPLS transport.
* **evpn.vlans** (global or node parameter): A list of EVPN-enabled VLANs. Default value with VXLAN transport: all global VLANs with **vni** parameter. There is no default value with MPLS transport.
* **evpn.session** (global or node parameter): A list of BGP session types on which the EVPN address family is enabled (default: `ibgp`)
* **evpn.as** (global parameter): Autonomous system number to use for VLAN and VRF route targets. Default value: **bgp.as** (when set globally) or **vrf.as**.
* **evpn.start_transit_vni** (system default parameter) -- the first symmetric IRB transit VNI, range 4096..16777215
* **evpn.start_transit_vlan** (device-dependent node parameter) -- the starting VLAN ID for VLANs used to map VXLAN transit VNIs

(evpn-vlan-service)=
### VLAN-Based Service Parameters

EVPN-related VLAN parameters are set on **vlans** dictionary. You can set the following parameters for every VLAN using VLAN-Based Service:

* **evpn.evi**: EVPN Instance identifier.
* **evpn.rd**: EVPN Instance route distinguisher (not checked at the moment). Default: **bgp.router_id**:**evpn.evi**
* **evpn.import** and **evpn.export**: Import and export route targets (not checked at the moment).

EVPN configuration module sets the following default EVI/RD/RT values for EVPN-enabled VLANs that are not part of a bundle service:

* **evpn.evi**: `vlan-id`
* **evpn.rd**: `router-id:evi` (according to Section 7.9 of RFC 7432 as the **evpn.evi** is set to **vlan.id**)
* **evpn.import** and **evpn.export**: `as:vlan-id` (according to Section 7.10 of RFC 7432 and Section 5.1.2.1 of RFC 8365)[^EAS]

[^EAS]: The AS number used in EVPN route targets is described in [](evpn-global-parameters).

(evpn-bundle-service)=
### EVPN Bundle Services

VLAN-Aware Bundle Service uses VRF configuration (and thus requires [VRF configuration module](vrf.md)). All EVPN-enabled VLANs belonging to a single VRF are configured as a bundle service, modeled as a single EVPN Instance.

[RD and RT values assigned by VRF module](vrf.md#rd-and-rt-values) are used to configure the VLAN bundle; you can set **evpn.evi** VRF parameter to set the EVPN Instance identifier. The default value of VRF EVPN Instance identifier is the **vrf.id**.

The EVPN bundle service is enabled with **evpn.bundle** VRF parameter that can take one of the following values:

* **vlan** -- VLAN bundle service (RFC 7432 section 6.2)
* **port** -- Port-based service (RFC 7432 section 6.2.1)
* **vlan_aware** -- VLAN-aware bundle service (RFC 7432 section 6.3)
* **port_aware** -- Port-based VLAN-aware service (RFC 7432 section 6.3.1)

### Integrated Routing and Bridging

IRB is configured whenever EVPN-enabled VLANs in a VRF contain IPv4 or IPv6 addresses:

* Asymmetric IRB requires no extra parameters (see [](evpn-asymmetric-irb) section for more details)
* Symmetric IRB used with VXLAN transport needs a transit VNI that has to be set with the **evpn.transit_vni** parameter.
* You can set the VRF EVI value with **evpn.evi** parameter.

The **evpn.transit_vni** parameter must specify a globally unique VNI value. It could be set to:

* *True*: EVPN configuration module auto-assigns a unique VNI to the VRF.
* An *integer value*: static VNI assignment, checked for uniqueness
* Name of *another VRF*: the **evpn.transit_vni** value is copied from that VRF. Use this setting for complex topologies where VRFs with different connectivity requirements have to share the transit VXLAN segment.

(evpn-asymmetric-irb)=
## Asymmetric IRB

Asymmetric IRB is a forwarding paradigm where the ingress PE-device performs routing between source and destination VLAN followed by EVPN bridging, while the egress PE-device performs bridging between EPVN transport (VXLAN or MPLS pseudowire) and destination VLAN.

To make asymmetric IRB work, all EVPN-enabled VLANs participating in a routing domain must be present on all participating PE-devices. EVPN configuration module strictly enforces that requirement -- every EVPN-enabled VLAN belonging to a VRF that uses asymmetric IRB must be present on every node on which the parent VRF is defined.

While you could define VLANs with a **vlans** attribute on every participating device, it's much easier to meet those requirements with a *group* of PE-devices, listing the VLANs participating in an asymmetric IRB routing domain in the group **vlans** attribute:

```
groups:
  hosts:
    members: [ h1, h2 ]
    device: linux
  switches:
    members: [ s1,s2 ]
    module: [ vlan,vxlan,ospf,bgp,evpn,vrf ]
    bgp.as: 65000
    vrfs:
      tenant:
        ospf: False
    vlans:
      red:
        vrf: tenant
      blue:
        vrf: tenant
```

```{tip}
Disable OSPF in a VRF using asymmetric IRB unless you connected external router(s) to one of the participating VLANs
```