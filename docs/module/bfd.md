# Bidirectional Forwarding Detection (BFD) Configuration Module

This configuration module configures the basic BFD ([RFC5880](https://datatracker.ietf.org/doc/html/rfc5880)) parameters. To configure fast failover with BFD, use the routing protocol [configuration modules](../module-reference.md). You can use BFD with [IS-IS](isis.md), [OSPF](ospf.md), and BGP (through the **[bgp.session](plugin-bgp-session)** plugin).

(bfd-platform)=
BFD is supported on these platforms:

```{features}
- title: BFD<br>protocol
  enabled: bfd
  caveats: bfd.caveats
- title: OSPF<br>with BFD
  enabled: ospf and bfd
- title: IS-IS<br>with BFD
  enabled: isis and bfd
- title: BGP<br>with BFD
  enabled: bgp.bfd
  caveats: bgp.bfd.caveats
```

```{tip}
See the integration test results for more details:

* [OSPFv2 test results](https://release.netlab.tools/_html/coverage.ospfv2)
* [OSPFv3 test results](https://release.netlab.tools/_html/coverage.ospfv3)
* [BGP sessions test results](https://release.netlab.tools/_html/coverage.bgp.session)
```

## Parameters

The following parameters can be set globally or per node/link:

* **min_tx**: The desired minimal interval for sending BFD packets, in msec.
* **min_rx**: The required minimal interval for receiving BFD packets, in msec
* **min_echo_rx**: Echo function timer, in msec
* **multiplier**: Number of missed packets before the session is considered down

Global defaults are set pretty high to accommodate a wide range of virtual network devices with varying quality of BFD implementation:

* **min_tx**: 1 second (1000 msec)
* **min_rx**: 1 second (1000 msec)
* **min_echo_rx**: disabled (set to zero)
* **multiplier**: 3

Valid intervals and ranges are platform-dependent. Some platforms have lower default values:

| platform | min-tx    | min-rx   |
|----------|-----------|----------|
| nxos     | 1000 msec | 500 msec |
| srlinux  | 100 msec  | 100 msec |
| sros     | 100 msec  | 100 msec |

## Example

To enable BFD using default values on all IS-IS interfaces:

```
module: [ isis, bfd ]

isis:
 bfd:
  ipv4: True
  ipv6: True
```
