# Bidirectional Forwarding Detection (BFD) Configuration Module

This configuration module configures the basic BFD ([RFC5880](https://datatracker.ietf.org/doc/html/rfc5880)) parameters. Routing protocol modules configure fast failover using BFD.

BFD configuration is supported on Arista EOS, Cisco IOS, Cisco IOS XE, Cisco NXOS, Nokia SR Linux and Nokia SROS.

The following routing protocols support BFD:

* [IS-IS](isis.md)
* [OSPF](ospf.md)

For routing protocol platform support please check the routing protocol configuration modules.

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
