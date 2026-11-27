(module-evpn)=
# Ethernet Virtual Private Network (EVPN) Configuration Module

This configuration module configures the BGP EVPN address family to implement L2VPN or L3VPN. It supports:

* VXLAN-based transport over IPv4 and IPv6
* MPLS-based transport using LDP- or SR-MPLS-assigned labels
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

(evpn-platform)=
## Platform Support

The following table describes the per-platform support of individual EVPN/VXLAN features:

```{features}
- title: VLAN-based<br>service
  enabled: vxlan and 'vxlan' in evpn.transport
  caveats: evpn.caveats.core
- title: VLAN Bundle<br>service
  enabled: vxlan and 'vxlan' in evpn.transport and evpn.bundle
- title: Asymmetric<br>IRB
  enabled: vxlan and 'vxlan' in evpn.transport and evpn.asymmetrical_irb
- title: Symmetric<br>IRB
  enabled: vxlan and 'vxlan' in evpn.transport and evpn.irb
  caveats: evpn.caveats.irb
```

The following table describes the per-platform support of individual EVPN/MPLS features:

```{features}
- title: VLAN-based<br>service
  enabled: mpls and 'mpls' in evpn.transport and vlan
- title: VLAN Bundle<br>service
  enabled: mpls and 'mpls' in evpn.transport and evpn.bundle
- title: Symmetric<br>IRB
  enabled: mpls and 'mpls' in evpn.transport
  caveats: evpn.caveats.mpls_irb
```

**Notes:**

* _netlab_ always uses symmetric IRB with EVPN/MPLS.
* Devices supporting [EVPN VLAN bundle services](evpn-bundle-service) implement only the VLAN-aware bundle service (see RFC 7432 section 6 for more details).

The following devices can be used as control-plane-only EVPN nodes (for example, EVPN route reflectors) but do not implement the EVPN data plane for the specified transport:

```{features}
- title: VXLAN
  enabled: "'vxlan' in evpn.bgp_session and 'vxlan' not in evpn.transport"
- title: MPLS
  enabled: "'mpls' in evpn.bgp_session and 'mpls' not in evpn.transport"
```

The EVPN module supports IBGP- and EBGP-based EVPN with VXLAN transport:

```{features}
- title: IBGP+IGP
  enabled: >-
    'ibgp' in evpn.bgp_session.vxlan
- title: EBGP-only
  enabled: >-
    'ebgp' in evpn.bgp_session.vxlan
  caveats: evpn.caveats.ebgp
- title: EBGP<br>Unnumbered
  enabled: >-
    'ebgp' in evpn.bgp_session.vxlan and bgp.ipv6_lla
```

With additional nerd knobs ([more details](evpn-weird-designs)), it's possible to implement the more convoluted designs, including:

* IBGP EVPN AF session established between loopback interfaces, advertised with underlay EBGP IPv4 AF
* EBGP EVPN AF session established between loopback interfaces advertised with underlay EBGP IPv4 AF (requires **ebgp.multihop** plugin)

```{features}
- title: IBGP over<br>EBGP
  enabled: >-
    'ibgp' in evpn.bgp_session.vxlan and bgp.local_as and bgp.activate_af
- title: EBGP<br>over EBGP
  enabled: >-
    'ebgp' in evpn.bgp_session.vxlan and bgp.multihop and bgp.activate_af
```

All devices supporting EVPN with VXLAN transport can use IPv4 VXLAN transport; some can also run VXLAN-over-IPv6:

```{features}
- title: IPv6 VXLAN<br>transport
  enabled: vxlan and 'vxlan' in evpn.transport and evpn.ipv6
```

```{warning}
* EVPN with VXLAN-over-IPv6 is enabled with the `defaults.vxlan.use_v6_vtep` attribute (see [](module-vxlan)). At the moment, you cannot run a control-plane-only EVPN node with IPv6 next hops.
* Arista EOS 4.35.2F and FRRouting 10.6.0 use incompatible encodings of PMSI_TUNNEL_ATTRIBUTE when running EVPN over IPv6 next hops. While each implementation works on its own, they are not interoperable.
```

(evpn-global-parameters)=
## Global EVPN Parameters

EVPN module supports these default/global/node parameters:

* **evpn.transport** (global): Transport to use, `vxlan` (default), `mpls` (MPLS with LDP-assigned labels), or `sr` (MPLS with SR-MPLS-assigned labels)
* **evpn.vrfs** (global or node parameter): A list of EVPN-enabled VRFs. The default value with VXLAN transport: all global VRFs with **evpn.transit_vni** parameter. There is no default value with MPLS transport.
* **evpn.vlans** (global or node parameter): A list of EVPN-enabled VLANs. The default value with VXLAN transport: all global VLANs with the **vni** parameter. There is no default value with MPLS transport.
* **evpn.session** (global or node parameter): A list of BGP session types on which the EVPN address family is enabled (default: `ibgp`)
* **evpn.as** (global parameter): Autonomous system number for VLAN and VRF route targets. Default value: **bgp.as** (when set globally) or **vrf.as**.
* **evpn.start_transit_vni** (system default parameter) -- the first symmetric IRB transit VNI, range 4096..16777215
* **evpn.start_transit_vlan** (device-dependent node parameter) -- the starting VLAN ID for VLANs used to map VXLAN transit VNIs
* **evpn.domain** (node parameter) -- EVPN domain (site) name. This parameter might have to be used in multi-site designs when you want to have an in-VRF inter-site EBGP session across an EVPN-controlled VLAN (see [](evpn-rp) for more details).

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

```{warning}
The devices that support EVPN bundle services (see the *VLAN Bundle service* column in the *Platform Support* table) currently support only the **vlan_aware** bundle service.
```

(evpn-irb)=
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

Finally, if you use EBGP with EVPN (simple EBGP, IBGP-over-EBGP, or EBGP-over-EBGP design), the PE devices have different AS numbers. _netlab_ thus tries to establish VRF EBGP sessions between them whenever they share a VLAN. However, the EVPN module removes such PE-to-PE intra-VRF EBGP sessions when:

* Both devices use the EVPN module
* The EBGP session is established across an EVPN-controlled VLAN
* The two devices use the same VRF name

This algorithm might remove an inter-site PE-to-PE EBGP session when you use Inter-AS Option A (EBGP sessions in VRFs) over EVPN-controlled VLANs. If that happens, use a different value of the **evpn.domain** parameter on nodes belonging to different sites (all nodes within a site must have the same **evpn.domain** value).

It might be even better to prevent the formation of VRF EBGP sessions between the PE devices:

* Use EVPN as a pure L3VPN (no stretched VLAN-over-VXLAN segments);
* Disable BGP in the EVPN-controlled VRFs with a setting similar to **vrfs._tenant_vrf_.bgp: False**;
* If you want to use BGP as the PE-CE routing protocol with stretched VLANs, disable BGP on stretched VLAN segments with a setting similar to **vlans._stretched_vlan_.bgp: False**.
