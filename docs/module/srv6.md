(module-srv6)=
# Segment Routing over IPv6 (srv6) Configuration Module

This configuration module configures SRv6 over IS-IS with IBGP using advertised SIDs for global and VPN connectivity services.

Supported SRv6 features:

* End SIDs (nodes) and End-x SIDs (links), all statically allocated
* IS-IS routing protocol with SRv6 TLVs
* SRv6 transport for global IPv4/IPv6 BGP routes
* BGP IPv4/IPv6 L3VPN over SRv6

The module currently depends on IS-IS and will trigger a configuration error if the **isis** module is not enabled in the network topology. It supports the L3VPN use case, as well as IPv4 islands over SRv6 (IPv4aaS) and IPv6 transport between SRv6 endpoints.

## Platform Support

The following table describes the per-platform support of SRv6-enabled routing protocols:

| Operating system   | IS-IS | OSPFv3 |
|--------------------|:--:|:-:|
| Cisco IOS XE[^XE]  | ✅ | ❌ |
| Cisco IOS XR[^XR]  | ✅ | ❌ |
| FRR                | ✅ | ❌ |

[^XE]: Includes Catalyst 8000v, Cisco IOL, and Cisco IOL layer-2 image. The minimum Cisco IOS/XE release with working SRv6 is release 17.16.01a.

[^XR]: Includes IOS XRv, IOS XRd, but not Cisco 8000v. Cisco 8000v does not support the *shift-only* microsegment behavior needed to interoperate with other SRv6 implementations. Please [open an issue](https://github.com/ipspace/netlab/issues/new/choose) if you're interested in running SRv6 on Cisco 8000v.

These platforms can use SRv6 next hops for global IPv4/IPv6 BGP routes:

| Operating system   | Global IPv4<br>BGP routes | Global IPv6<br>BGP routes | 
|--------------------|:--:|:-:|
| Cisco IOS XR       | ✅ | ✅ |
| FRR                | ✅ | ✅ |

These platforms support SRv6-based L3VPN services:

| Operating system      | VPNv4 | VPNv6 |
| ----------------------| :---: | :---: |
| Cisco IOS XE[^XE]     |   ✅  |  ✅  |
| Cisco IOS XR[^XR]     |   ✅  |  ✅  |
| FRR                   |   ✅  |  ✅ [❗️](caveats-frr)  |

**Notes**
* VPNv4 and VPNv6 address families are enabled on IPv6 IBGP sessions

## Configurable Global and Node Parameters

* **addressing.srv6_locator** -- global address pool[^poolname] for allocation of SRv6 locator prefixes, the default prefix is defined in `topology.defaults.srv6.locator_pool` (5F00::/16, the IANA reserved range defined by [RFC9602](https://datatracker.ietf.org/doc/rfc9602/)
* **srv6.allocate_loopback** -- global flag (default: `False`) to replace the IPv6 loopback address of each SRv6-enabled node with an IPv6 address allocated from the locator range
* **srv6.bgp** -- enable BGP with IPv4 and IPv6 address families over SRv6, default IPv4 + IPv6 over iBGP.
* **srv6.vpn** -- enable BGP with VPNv4 and VPNv6 address families over SRv6. BGP/SRv6 L3VPN is disabled by default.
* **srv6.igp** -- list of IGP protocols for which to enable SRv6, default `[isis]`

[^poolname]: You can change the name of the default SRv6 locator pool with the `topology.defaults.const.srv6.locator_pool.name` parameter

(srv6-node-parameters)=
## Node Parameters

* **srv6.locator**: an optional IPv6 address prefix to allocate to a given SRv6 node; by default, each node is assigned a unique /48 prefix from the global pool
* **srv6.transit_only**: an optional Boolean flag to optimize resource usage and only allocate transit behaviors, not endpoint behaviors

## Configurable BGP/SRv6 IPv4/6 and L3VPN Parameters

This module provides 2 parameters that are identical in structure, controlling different BGP address families:

* **srv6.bgp** -- Controls SRv6 next hops for global IPv4 and IPv6 BGP routes
* **srv6.vpn** -- Controls VPNv4 and VPNv6 address families

Each parameter could be a boolean (*True* to enable both IP address families on IBGP sessions), or a dictionary of parameters:

* **ipv4** -- enable IPv4/VPNv4 address family
* **ipv6** -- enable IPv6/VPNv6 address family

**ipv4** and **ipv6** parameters could be:

* Boolean value *False* to disable the address family within node data (overwriting global defaults)
* Boolean value *True* to enable the address family on IBGP sessions
* A string or a list of *ibgp/ebgp* keywords[^NE]

For a tested example, see the [SRv6 integration tests](https://github.com/ipspace/netlab/tree/dev/tests/integration/srv6).

[^NE]: SRv6 services over EBGP are currently not supported
