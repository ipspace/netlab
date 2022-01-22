# Segment Routing over IPv6 (srv6) Configuration Module

This configuration module configures SRv6 over IS-IS and (optionally) BGP on Nokia SR OS.

Supported SRv6 features:

* End SIDs (nodes) and End-x SIDs (links), all statically allocated
* IS-IS routing protocol with SRv6 TLVs
* Dynamic BGP Service SIDs

The module currently depends on IS-IS module and will trigger a configuration error if the **isis** module is not enabled in the network topology.

## Parameters

* Locator: an IPv6 address range to allocate to SRv6 nodes; each node is assigned a unique /64 prefix from this range

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
    unnumbered: true
  loopback:
    ipv6: 2001:db8:cafe::/48

srv6.locator: 2001:db8:aaaa::/48  # Must not overlap with interfaces
```

```
provider: clab
defaults.device: sros # Type must support FP4 chipset

nodes:
  e1:
  e2:
  c1:
  c2:
```

The devices are connected into a square topology:

```
links:
- e1-c1
- e1-c2
- e2-c1
- e2-c2
```
