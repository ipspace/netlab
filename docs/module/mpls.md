# MPLS Configuration Module

MPLS configuration module implements traditional MPLS control plane using LDP- or BGP-based label distribution. Segment routing for MPLS is implemented in a [separate configuration module](sr-mpls.md).

Supported features:

* LDP within an autonomous system
* BGP Labeled Unicast over IBGP and/or EBGP sessions for IPv4 and IPv6
 
The following table describes per-platform support of individual MPLS label distribution features:

| Operating system  | LDP   | BGP LU |
| ------------------| :---: | :----: |
| Arista EOS        |   ✅  |   ✅   |
| Cisco IOS         |   ✅  |   ✅   |
| Cisco IOS XE      |   ✅  |   ✅   |

## Configurable Global and Node Parameters

* **mpls.ldp** -- enable LDP on intra-AS links (see [common routing protocol features](routing.md)) for more details.
* **mpls.bgp** -- enable BGP Labeled Unicast address families.

## Configurable Link and Interface Parameters

* **mpls.ldp** (boolean) -- enable or disable LDP and MPLS encapsulation on the interface.

## Configurable LDP Parameters

**mpls.ldp** global/node setting could be a boolean (*True*: enable LDP) or a dictionary of parameters:

* **router_id** -- Router ID to be used for LDP. Should correspond to a reachable loopback IP address.
* **igp_sync** (boolean) -- Enable LDP/IGP synchronization

## Configurable BGP LU Parameters

**mpls.bgp** could be:

* A boolean: *True* enables BGP LU on all BGP sessions;
* A list of BGP session types on which BGP LU should be enabled  for all address families (*ibgp* and/or *ebgp*)
* A dictionary of address families, each one of them being a list of session types.
