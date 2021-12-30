# Bidirectional Forwarding Detection (BFD) Configuration Module

This configuration module configures BFD([RFC5880](https://datatracker.ietf.org/doc/html/rfc5880)) for IS-IS on SR Linux and SROS devices.

Supported IGP protocols:
* IS-IS

The module is currently focused on supporting BFD with IS-IS interfaces, other protocols and devices can be added over time.

## Parameters
The following parameters can be set globally or per node/link:
* min_tx_interval_us: The desired minimal interval for sending BFD packets, in us
* min_rx_interval_us: The required minimal interval for receiving BFD packets, in us
* min_echo_rx_interval_us: Echo function, 0(default) = disabled
* detection_multiplier: Number of missed packets before the session is considered down

## Example
To enable BFD for all IS-IS interfaces:
```
isis:
 bfd:
  ipv4: True
  ipv6: True
```
