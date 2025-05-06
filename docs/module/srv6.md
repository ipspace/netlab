# Segment Routing over IPv6 (srv6) Configuration Module

This configuration module configures SRv6 over IS-IS with IBGP to advertise SID reachability

Supported SRv6 features:

* End SIDs (nodes) and End-x SIDs (links), all statically allocated
* IS-IS routing protocol with SRv6 TLVs
* Dynamic BGP Service SIDs
* BGP L3VPN v4/v6 over SRv6

The module currently depends on IS-IS and will trigger a configuration error if the **isis** module is not enabled in the network topology.
It is initially focused around intra-AS IBGP scenarios, EBGP can be configured but may require additional configuration.

## Platform Support
The following table describes per-platform support of individual router-level SRv6 features:

| Operating system         | IS-IS | OSPFv3 | BGP v4/v6 | Transit only |
| ------------------------ |:-----:|:------:|:---------:|:-------------:
| FRR                      |   ✅  |   ❌   |    ❌     |      ❌      | 
| Nokia SR OS              |   ✅  |   ❌   |    ✅     |      ✅      |

(srv6-l3vpn-supported-platforms)=
### BGP/SRv6 L3VPN

| Operating system      | VPNv4 | VPNv6 |
| ----------------------| :---: | :---: |
| FRR                   |   ✅  |   ✅  |
| Nokia SR OS           |   ❌  |   ❌  |

**Notes**
* VPNv4 and VPNv6 address families are enabled on IPv6 IBGP/EBGP sessions

## Configurable Global and Node Parameters

* **addressing.srv6_locator** -- global address pool[^poolname] for allocation of SRv6 locator prefixes, default prefix defined by `topology.defaults.srv6.locator_pool` 
                                 (5F00::/16, the IANA reserved range defined by [RFC9602](https://datatracker.ietf.org/doc/rfc9602/)
* **srv6.allocate_loopback** -- global flag (default: `True`) to replace the IPv6 loopback address of each SRv6-enabled node with an IP allocated from the locator range
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
* **srv6.bgp** -- Controls IPv4 and IPv6 address families
* **srv6.vpn** -- Controls VPNv4 and VPNv6 address families

Each parameter could be a boolean (*True* to enable both IP address families on IBGP sessions), or a dictionary of parameters:

* **ipv4** -- enable IPv4/VPNv4 address family
* **ipv6** -- enable IPv6/VPNv6 address family

**ipv4** and **ipv6** parameters could be:

* Boolean value *False* to disable the address family within node data (overwriting global defaults)
* Boolean value *True* to enable the address family on IBGP sessions
* A string or a list of *ibgp/ebgp* keywords

## Example

We want to create a small two-router SRv6 network to connect disjointed IPv4 networks over a IPv6-only core

Both devices run SRv6 with IS-IS and iBGP:
```
module: [ isis, srv6, bgp ]
bgp.as: 65000                # single iBGP AS
```

We want to use IPv6-only P2P interfaces and IPv4-only LAN connections with IPv6 configured on loopback addresses:

```
addressing:
  p2p:
    ipv4: False
    ipv6: True               # IPv6-only core
  lan:
    ipv4: 10.0.0.0/24
    ipv6: False
  srv6_locator:
    ipv6: 5F00::/40          # Must not overlap with interfaces, this is from the IANA reserved range
    prefix6: 48              # Assign a /48 to each node
  loopback:
    ipv4: False
    ipv6: 5F00::/40          # Using loopbacks in the locator range (different for each SRv6 node)

provider: clab
defaults.device: frr

groups:
  _auto_create: True
  core:
    members: [ pe1, pe2 ]
  clients:
    members: [ c1, c2 ]
    device: linux
```

The devices are connected into a linear topology:
```
links:
- c1-pe1
- pe1-pe2
- pe2-c2
```
