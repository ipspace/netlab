# Ethernet Virtual Private Network (EVPN) Configuration Module

This configuration module configures the BGP EVPN address family to implement L2VPN or L3VPN. It supports:

* VXLAN-based transport over IPv4 and IPv6
* MPLS-based transport
* VLAN-Based Service (bridging of a single VLAN within an EVPN Instance)
* VLAN-Aware Bundle Service (bridging of multiple related VLANs inside a single EVPN Instance)
* Symmetric and asymmetric IRB
* Layer-3-only VPN (L3VPN) with symmetric IRB
* Most EVPN design scenarios, including the convoluted ones like IBGP-over-EBGP or EBGP-over-EBGP.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes the per-platform support of individual EVPN/VXLAN features:

| Operating system   | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  |  ✅  | ✅  | ✅  |
| Aruba AOS-CX       | ✅  |  ❌  | ✅  | ✅[❗](caveats-aruba)  |
| Cisco Nexus OS     | ✅  |  ❌  | ✅  | ✅  |
| Cumulus Linux 4.x  | ✅  |  ❌  | ✅  | ✅  |
| Cumulus 5.x (NVUE) | ✅  |  ❌  | ✅  | ✅  |
| Dell OS 10         | ✅  |  ❌  | ✅  | ✅  |
| FRR                | ✅  |  ❌  | ✅  | ✅  |
| Nokia SR Linux     | ✅  |  ✅  | ✅  | ✅  |
| Nokia SR OS        | ✅  |  ❌  | ✅  | ✅  |
| vJunos-switch [❗](caveats-vjunos-switch) | ✅  |  ❌  | ✅  | ✅  |
| VyOS               | ✅  |  ❌  | ✅  | ✅  |

The following table describes the per-platform support of individual EVPN/MPLS features:

| Operating system   | VLAN-based<br>service | VLAN Bundle<br>service | Asymmetric<br>IRB | Symmetric<br>IRB |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  |  ❌  |  ❌  |

```{note}
* Arista EOS requires an anycast gateway for EVPN/MPLS symmetric IRB configuration.
```

Devices supporting [EVPN VLAN bundle services](evpn-bundle-service) implement the following bundle service types (see RFC 7432 section 6 for more details):

| Operating system   | VLAN<br>bundle | Port<br>service | VLAN-aware<br>bundle | Port-based<br>VLAN bundle |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         |  ❌  |  ❌  | ✅  |  ❌  |
| Nokia SR Linux     |  ❌  |  ❌  | ✅  |  ❌  |

EVPN module supports IBGP- and EBGP-based EVPN:

| Operating system   | IBGP+IGP | BGP RR | EBGP-only | EBGP<br>Unnumbered |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX       | ✅  | ✅  | ❌   | ❌   |
| Cisco Nexus OS     | ✅  | ✅  | ✅  | ❌   |
| Cumulus Linux 4.x  | ✅  | ✅  | ✅  | ✅  |
| Cumulus 5.x (NVUE) | ✅  | ✅  | ✅  | ✅  |
| Dell OS 10 [❗](caveats-os10) | ✅  | ✅  | ✅  | ✅  |
| FRR                | ✅  | ✅  | ✅  | ✅  |
| Nokia SR Linux     | ✅  | ✅  | ✅  | ✅  |
| Nokia SR OS        | ✅  | ✅  | ✅  |  ❌  |
| vJunos-switch      | ✅  | ✅  |  ❌  |  ❌  |
| VyOS               | ✅  | ✅  |  ❌  | ✅  |

With additional nerd knobs ([more details](evpn-weird-designs)), it's possible to implement the more convoluted designs, including:

* IBGP EVPN AF session established between loopback interfaces, advertised with underlay EBGP IPv4 AF
* EBGP EVPN AF session established between loopback interfaces advertised with underlay EBGP IPv4 AF (requires **ebgp.multihop** plugin)

| Operating system   | IBGP over<br>EBGP | EBGP<br>over EBGP |
| ------------------ | :-: | :-: |
| Arista EOS         | ✅  | ✅  |
| Aruba AOS-CX       | ✅  | ✅  |
| Cisco Nexus OS     | ❌   | ❌   |
| Cumulus Linux 4.x  | ✅  | ✅  |
| Cumulus 5.x (NVUE) | ✅  | ✅  |
| Dell OS 10         | ✅  | ❌   |
| FRR                | ✅  | ✅  |
| Nokia SR Linux     | ✅  | ✅  |
| Nokia SR OS        | ✅  | ✅  |
| vJunos-switch      | ✅  | ✅   |
| VyOS               | ✅  | ❌   |

Most EVPN/VXLAN implementations support only IPv4 VXLAN transport; some can run VXLAN-over-IPv6:

| Operating system   | IPv4 VXLAN<br>transport | IPv6 VXLAN<br>transport |
| ------------------ | :-: | :-: |
| Arista EOS         | ✅  | ❌   |
| Aruba AOS-CX       | ✅  | ❌   |
| Cisco Nexus OS     | ✅  | ❌   |
| Cumulus Linux 4.x  | ✅  | ❌   |
| Cumulus 5.x (NVUE) | ✅  | ❌   |
| Dell OS 10         | ✅  | ❌   |
| FRR                | ✅  | ✅  |
| Nokia SR Linux     | ✅  | ❌   |
| Nokia SR OS        | ✅  | ❌   |
| vJunos-switch      | ✅  | ❌   |
| VyOS               | ✅  | ❌ [❗](caveats-vyos)   |

(evpn-global-parameters)=
## Global EVPN Parameters

EVPN module supports these default/global/node parameters:

* **evpn.transport** (global): Transport to use, `vxlan` (default) or `mpls`
* **evpn.vrfs** (global or node parameter): A list of EVPN-enabled VRFs. The default value with VXLAN transport: all global VRFs with **evpn.transit_vni** parameter. There is no default value with MPLS transport.
* **evpn.vlans** (global or node parameter): A list of EVPN-enabled VLANs. The default value with VXLAN transport: all global VLANs with the **vni** parameter. There is no default value with MPLS transport.
* **evpn.session** (global or node parameter): A list of BGP session types on which the EVPN address family is enabled (default: `ibgp`)
* **evpn.as** (global parameter): Autonomous system number for VLAN and VRF route targets. Default value: **bgp.as** (when set globally) or **vrf.as**.
* **evpn.start_transit_vni** (system default parameter) -- the first symmetric IRB transit VNI, range 4096..16777215
* **evpn.start_transit_vlan** (device-dependent node parameter) -- the starting VLAN ID for VLANs used to map VXLAN transit VNIs

(evpn-vlan-service)=
### VLAN-Based Service Parameters

EVPN-related VLAN parameters are set on the **vlans** dictionary. You can set the following parameters for every VLAN using VLAN-Based Service:

* **evpn.evi**: EVPN Instance identifier.
* **evpn.rd**: EVPN Instance route distinguisher. Default: **bgp.router_id**:**evpn.evi**
* **evpn.import** and **evpn.export**: Import and export route targets (not currently checked).

EVPN configuration module sets the following default EVI/RD/RT values for EVPN-enabled VLANs that are not part of a bundle service:

* **evpn.evi**: `vlan-id`
* **evpn.rd**: `router-id:evi` (according to Section 7.9 of RFC 7432, as the **evpn.evi** is set to **vlan.id**)
* **evpn.import** and **evpn.export**: `as:vlan-id` (according to Section 7.10 of RFC 7432 and Section 5.1.2.1 of RFC 8365)[^EAS]

[^EAS]: The AS number used in EVPN route targets is described in [](evpn-global-parameters).

(evpn-bundle-service)=
### EVPN Bundle Services

VLAN-Aware Bundle Service uses VRF configuration (and thus requires [VRF configuration module](vrf.md)). All EVPN-enabled VLANs belonging to a single VRF are configured as a bundle service, modeled as a single EVPN Instance.

[RD and RT values assigned by VRF module](vrf.md#rd-and-rt-values) are used to configure the VLAN bundle; you can set **evpn.evi** VRF parameter to set the EVPN Instance identifier. The default value of the VRF EVPN Instance identifier is the **vrf.id**.

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

Asymmetric IRB is a forwarding paradigm in which the ingress PE device performs routing between the source and destination VLANs, followed by EVPN bridging—the egress PE device bridges between EVPN transport (VXLAN or MPLS pseudowire) and the destination VLAN.

To make asymmetric IRB work, all EVPN-enabled VLANs participating in a routing domain must be present on all participating PE devices. The EVPN configuration module strictly enforces that requirement; every EVPN-enabled VLAN belonging to a VRF that uses asymmetric IRB must be present on every node on which the parent VRF is defined.

While you could define VLANs with a **vlans** attribute on every participating device, it's much easier to meet those requirements with a *group* of PE devices, listing the VLANs participating in an asymmetric IRB routing domain in the group **vlans** attribute:

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
Disable routing protocols in a VRF using asymmetric IRB unless you connected external router(s) to one of the participating VLANs (see also [](evpn-rp))
```

(evpn-weird-designs)=
## Convoluted EVPN Designs

Implementing mainstream EVPN designs (IBGP+IGP, EBGP) with _netlab_ topologies is trivial; more convoluted designs require additional BGP features or plugins:

* **IBGP-over-EBGP** design assigns the same BGP AS number to all nodes (triggering IBGP EVPN sessions) and uses **bgp.local_as** on links to force EBGP sessions between adjacent nodes. Furthermore, you must limit the activation of IPv4 address family to EBGP sessions, and turn off IBGP-without-IGP warning ([sample topology](https://github.com/ipspace/netlab/blob/dev/tests/integration/evpn/12-vxlan-ibgp-ebgp.yml))
* **EBGP-over-EBGP** design uses **[ebgp.multihop](plugin-ebgp-multihop)** plugin to establish additional EBGP sessions between device loopbacks. You have to activate EVPN AF on multihop EBGP sessions and limit IPv4 AF to direct EBGP sessions ([sample topology](https://github.com/ipspace/netlab/blob/dev/tests/integration/evpn/14-vxlan-ebgp-ebgp.yml)).

Before using any design involving EBGP, please read [](evpn-rp).

(evpn-rp)=
## Interactions with Routing Protocols

Like the [VXLAN case](vxlan-rp), _netlab_ enables all routing protocols configured on a node on EVPN-controlled VLANs. 

That could result in severe routing instabilities. You should turn off routing protocols on EVPN-controlled VLANs (use a setting similar to **vlans._name_.ospf: False**), put EVPN-controlled VLANs in a VRF, or make them layer-2-only VLANs with **vlan.mode** set to **bridge**.

If you're using EVPN to implement symmetrical IRB (**evpn.transit_vni** is set in a VRF), turn off routing protocols in the VRF unless you use the VRF to connect to CE-routers. Otherwise, the routers establish in-VRF IGP adjacencies over extended VLANs and use in-VRF IGP routes instead of EVPN routes for end-to-end connectivity.

If you want to implement an EVPN L3VPN with CE-routers, use separate segments (not VXLAN-backed VLANs) for PE-CE connectivity. There is no way to block the establishment of PE-to-PE in-VRF IGP adjacencies if you expect to have the PE-CE IGP adjacencies on a VXLAN-backed VLAN.

Finally, if you use EBGP with EVPN (simple EBGP, IBGP-over-EBGP, or EBGP-over-EBGP design), the PE devices have different AS numbers, and _netlab_ tries to establish VRF EBGP sessions between them whenever they share a VLAN. To prevent the formation of VRF EBGP sessions between the PE devices:

* Use EVPN as a pure L3VPN (no stretched VLAN-over-VXLAN segments);
* Disable BGP in the EVPN-controlled VRFs with a setting similar to **vrfs._tenant_vrf_.bgp: False**;
* If you want to use BGP as the PE-CE routing protocol with stretched VLANs, disable BGP on stretched VLAN segments with a setting similar to **vlans._stretched_vlan_.bgp: False**.
