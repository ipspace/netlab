# Segment Routing over IPv6 (srv6) Configuration Module

This configuration module configures SRv6 over IS-IS and (optionally) BGP and L3VPN

Supported SRv6 features:

* End SIDs (nodes) and End-x SIDs (links), all statically allocated
* IS-IS routing protocol with SRv6 TLVs
* Dynamic BGP Service SIDs

The module currently depends on IS-IS module and will trigger a configuration error if the **isis** module is not enabled in the network topology.

## Platform Support
The following table describes per-platform support of individual router-level SRv6 features:

| Operating system         | IS-IS | OSPFv3 | BGP v4/v6 |
| ------------------------ |:-----:|:------:|:---------:|
| FRR                      |   ✅  ||  ❌   |     ✅    |
| Nokia SR OS              |   ✅  ||  ❌   |     ✅    |

(srv6-l3vpn-supported-platforms)=
### BGP/SRv6 L3VPN

| Operating system      | VPNv4 | VPNv6 |
| ----------------------| :---: | :---: |
| FRR                   |   ✅  |   ✅  |

**Notes**
* VPNv4 and VPNv6 address families are enabled on IPv6 IBGP/EBGP sessions

## Configurable Global and Node Parameters

* **addressing.srv6_locator** -- global address pool for allocation of SRv6 locator prefixes, default prefix defined by `topology.defaults.srv6.locator_pool`
* **srv6.af**  -- IP address families to enable in the overlay, default IPv4 + IPv6
* **srv6.bgp** -- enable SRv6 for BGP when module is available, default `True`
* **srv6.vpn** -- enable VPNv4 and VPNv6 address families over SRv6. BGP/SRv6 L3VPN is disabled by default.
* **srv6.igp** -- list of IGP protocols for which to enable SRv6, default `[isis]`

(srv6-node-parameters)=
## Node Parameters

* **srv6.locator**: an optional IPv6 address prefix to allocate to a given SRv6 node; by default, each node is assigned a unique /48 prefix from the global pool
* **srv6.transit_only**: an optional Boolean flag to optimize resource usage and only allocate transit behaviors, not endpoint behaviors

## Configurable BGP/SRv6 L3VPN Parameters

**srv6.vpn** could be a boolean (*True* to enable all possible L3VPN address families on IBGP sessions), or a dictionary of parameters:

* **ipv4** -- enable VPNv4 address family
* **ipv6** -- enable VPNv6 address family

**ipv4** and **ipv6** parameters could be:

* Boolean value *False* to disable VPN address family within node data (overwriting global defaults)
* Boolean value *True* to enable VPN address family on IBGP sessions
* A string or a list of *ibgp/ebgp* keywords

## Example

We want to create a four-router SRv6 network.

All devices run IS-IS and SRv6:
```
module: [ isis, srv6 ]
```

We want to use unnumbered P2P interfaces and dual-stack deployment with IPv6 configured on loopback addresses:

```
addressing:
  p2p:
    ipv6: true
  loopback:
    ipv6: 2001:db8:cafe::/48
  srv6_locator:
    ipv6: 2001:aa::/40       # Must not overlap with interfaces
    prefix6: 48              # Assign a /48 to each node

provider: clab
defaults.device: frr

groups:
  _auto_create: True
  nodes:
    members: [ e1, e2, c1, c2 ]
```

The devices are connected into a square topology:
```
links:
- e1-c1
- e1-c2
- e2-c1
- e2-c2
```
