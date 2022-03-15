# MPLS Configuration Module

MPLS configuration module implements traditional MPLS control plane using LDP- or BGP-based label distribution. Segment routing for MPLS is implemented in a [separate configuration module](sr-mpls.md).

Supported features:

* LDP within an autonomous system
* BGP Labeled Unicast (LU) over IBGP and/or EBGP sessions for IPv4 and IPv6
 
The following table describes per-platform support of individual MPLS label distribution features:

| Operating system  | LDP   | Exp.Null | IGP sync | Advertise<br>filter |
| ------------------| :---: | :------: | :--: | :--: |
| Arista EOS        |   ✅  |   ✅    |   ❌  |   ❌  |
| Cisco IOS         |   ✅  |   ✅    |   ❌  |   ❌  |
| Cisco IOS XE      |   ✅  |   ✅    |   ❌  |   ❌  |

| Operating system  | BGP LU | Exp.Null |
| ------------------| :----: | :------: |
| Arista EOS        |   ✅   |    ❌     |
| Cisco IOS         |   ✅   |    ✅    |
| Cisco IOS XE      |   ✅   |    ✅    |

## Configurable Global and Node Parameters

* **mpls.ldp** -- enable LDP on intra-AS links (see [common routing protocol features](routing.md)) for more details.
* **mpls.bgp** -- enable BGP Labeled Unicast address families.

## Configurable Link and Interface Parameters

* **mpls.ldp** (boolean) -- enable or disable LDP and MPLS encapsulation on the interface.

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
