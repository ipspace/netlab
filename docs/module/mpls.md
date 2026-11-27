(module-mpls)=
# MPLS Configuration Module

The MPLS configuration module implements:

* LDP-based label distribution
* BGP labeled unicast over IBGP and/or EBGP sessions for IPv4 and IPv6
* MPLS/VPN vpnv4 and vpnv6 address families for IBGP and EBGP (inter-AS option B) sessions
* 6PE over IBGP and/or EBGP sessions

Segment routing for MPLS is implemented in a [separate configuration module](sr-mpls.md).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(mpls-platform)=
## Platform Support

The following table describes the per-platform support of individual MPLS label distribution features:

### Label Distribution Protocol (LDP)

```{features}
- title: LDP
  enabled: mpls.ldp
  caveats: mpls.caveats.core
- title: Explicit<br>null
  enabled: mpls.ldp.explicit_null
- title: IGP<br>sync
  enabled: mpls.ldp.igp_sync
```

**Notes:**
* LDP is enabled on all non-VRF intra-AS interfaces with IPv4 addresses.
* No platform implements the **mpls.ldp.advertise** attribute.
* To disable LDP on an intra-AS interface or enable it on an inter-AS or VRF interface, use the **mpls.ldp** link/interface parameter.

### BGP Labeled Unicast (BGP-LU)

```{features}
- title: BGP LU
  enabled: mpls.bgp
- title: Explicit<br>null
  enabled: mpls.bgp.explicit_null
- title: Disable<br>unlabeled
  enabled: mpls.bgp.disable_unlabeled
```

**Notes**
* Cisco IOS merges labeled and unlabeled BGP routes.
* You might have to disable unlabeled address families on Arista EOS

(mpls-l3vpn-supported-platforms)=
### BGP/MPLS L3VPN

```{features}
- title: VPNv4
  enabled: mpls.vpn is True or 'ipv4' in mpls.vpn
  caveats: mpls.caveats.core
- title: VPNv6
  enabled: mpls.vpn is True or 'ipv6' in mpls.vpn
```

**Notes**
* VPNv4 and VPNv6 address families are enabled on IPv4 IBGP/EBGP sessions
* On Mikrotik RouterOS BGP configuration/implementation, adding the VPNv4 AFI will completely overwrite the AFI supported list for the peer with "ip,vpnv4" (current template limitation). Given the general limitations of ROSv6 on IPv6, this should not be such a big problem.

### 6PE

```{features}
- title: 6PE
  enabled: mpls['6pe']
```

**Notes**

* You cannot enable 6PE and IPv6 BGP-LU on the same node.

(mpls-params)=
## Configurable Global and Node Parameters

* **mpls.ldp** -- enable LDP on intra-AS links (see [common routing protocol features](routing.md)) for more details.
* **mpls.bgp** -- enable BGP Labeled Unicast address families. BGP-LU is disabled by default.
* **mpls.vpn** -- enable VPNv4 and VPNv6 address families. BGP/MPLS L3VPN is disabled by default.
* **mpls.6pe** -- enable 6PE on IBGP and/or EBGP sessions (default: IBGP only). 6PE is disabled by default.

LDP is enabled by default on all nodes using the **mpls** configuration module, and can be disabled by setting **mpls.ldp** node parameter to *False*.

```{warning}
* MPLS-based BGP services are not supported over IBGP local-as sessions due to the required BGP next-hop changes on IBGP sessions.
* LDP requires an IGP and the IPv4 address family on the node.
* BGP-LU, BGP/MPLS L3VPN, and 6PE require the BGP configuration module. 6PE also requires the IPv4 address family within the BGP routing process.
```

## Configurable Link and Interface Parameters

* **mpls.ldp** (boolean) -- enable or disable LDP and MPLS encapsulation on the interface.

LDP is enabled by default on all intra-AS interfaces in the global routing table. To enable LDP on an inter-AS or VRF interface, set the **mpls.ldp** link- or interface parameter to *True*.

## Configurable LDP Parameters

**mpls.ldp** global/node setting could be a boolean (*True*: enable LDP) or a dictionary of parameters:

* **router_id** -- Router ID to be used for LDP. Should correspond to a reachable loopback IP address.
* **igp_sync** (boolean) -- Enable LDP/IGP synchronization
* **explicit_null** (boolean) -- Enable Explicit Null advertisement
* **advertise** -- list of link roles to advertise (including *loopback* pseudo-role). The default behavior is device-specific.

## Configurable BGP LU Parameters

**mpls.bgp** could be a boolean (*True* to enable all possible BGP LU sessions), or a dictionary of parameters:

* **ipv4** -- enable BGP LU for IPv4 unicast address family
* **ipv6** -- enable BGP LU for IPv6 unicast address family
* **explicit_null** -- advertise Explicit Null labels on BGP LU sessions
* **disable_unlabeled** -- disable IPv4/IPv6 address families when enabling BGP-LU address families.

**ipv4** and **ipv6** parameters could be:

* Boolean value *False* to disable BGP-LU sessions for an address family within node data (overwriting global defaults)
* Boolean value *True* to enable BGP-LU on IBGP and EBGP sessions
* A string or a list of *ibgp/ebgp* keywords

In the following example, BGP-LU is enabled on IBGP and EBGP sessions for IPv4 and for IBGP sessions for IPv6:

```
mpls:
  bgp:
    ipv4: True
    ipv6: [ ibgp ]
```

## Configurable BGP/MPLS L3VPN Parameters

**mpls.vpn** could be a boolean (*True* to enable all possible L3VPN address families on IBGP sessions), or a dictionary of parameters:

* **ipv4** -- enable VPNv4 address family
* **ipv6** -- enable VPNv6 address family

**ipv4** and **ipv6** parameters could be:

* Boolean value *False* to disable VPN address family within node data (overwriting global defaults)
* Boolean value *True* to enable VPN address family on IBGP sessions
* A string or a list of *ibgp/ebgp* keywords

To enable intra-AS MPLS/VPN, set **mpls.vpn** to *True*. The VPN address families will be enabled according to the address families configured in VRFs.

```
mpls.vpn: True
```

To enable inter-AS MPLS/VPN (Option B), set **mpls.vpn** to `[ ibgp, ebgp ]`. You can configure inter-AS MPLS/VPN for an individual address family or all address families configured in VRFs.

The following example enables inter-AS MPLS/VPN for the whole lab topology and disables it for VPNv6 address family on PE1:

```
mpls.vpn: [ ibgp, ebgp ]

nodes:
  pe1:
    mpls.vpn.ipv4: [ ibgp, ebgp ]
    mpls.vpn.ipv6: [ ibgp ]
```

## Configurable 6PE Parameters

**mpls.6pe** is a global or node parameter that could be a boolean (*True* to enable 6PE on IBGP sessions) or a list of session types (*ibgp* and/or *ebgp*).
