# Bidirectional Forwarding Detection (BFD) Configuration Module

This configuration module configures BFD ([RFC5880](https://datatracker.ietf.org/doc/html/rfc5880)) for IS-IS on SR Linux and SROS devices.

Supported IGP protocols:

* IS-IS

The module is currently focused on supporting BFD with IS-IS interfaces, other protocols and devices can be added over time.

## Parameters

The following parameters can be set globally or per node/link:

* **min_tx**: The desired minimal interval for sending BFD packets, in msec.
* **min_rx**: The required minimal interval for receiving BFD packets, in msec
* **min_echo_rx**: Echo function, in msec
* **multiplier**: Number of missed packets before the session is considered down

Global defaults are set pretty high to accommodate a wide range of virtual network devices with varying quality of BFD implementation:

* **min_tx**: 1 second (1000 msec)
* **min_rx**: 1 second (1000 msec)
* **min_echo_rx**: disabled (set to zero)
* **multiplier**: 3

Valid intervals and ranges are platform-dependent. Some platforms have lower default values:

| platform | min-tx   | min-rx   |
|----------|----------|----------|
| srlinux  | 100 msec | 100 msec |
| sros     | 100 msec | 100 msec |

## Example

To enable BFD using default values on all IS-IS interfaces:

```
module: [ isis, bfd ]

isis:
 bfd:
  ipv4: True
  ipv6: True
```
