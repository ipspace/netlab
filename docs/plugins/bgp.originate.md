# BGP Network Origination Plugin

The **bgp.originate** modifies the way _netlab_ configures BGP network origination. The [](../module/bgp.md) configures static routes to the Null interface to originate additional IPv4 prefixes and does not support IPv6 prefixes.

This plugin creates a loopback interface for every originated prefix, which can be either an IPv4 or an IPv6 prefix. The loopback interface gets the first IP address in the advertised prefix.

The plugin works with all platforms supporting the [](../module/bgp.md) and [loopback interfaces](platform-initial-interfaces).

| Modified attributes      | Meaning |
|--------------------------|---------|
| **bgp.originate** (node) | A list of IPv4 or IPv6 prefixes to originate |

## Example

In the following topology, R1 originates three prefixes -- its loopback IP address, another IPv4 prefix, and an IPv4 prefix.

```
defaults.device: eos

module: [ bgp ]
bgp.as: 65000
plugin: [ bgp.originate ]

nodes:
  r1:
    bgp.originate:
    - 172.16.17.0/28
    - 2000:db8:cafe::0/96

links: [ r1 ]
```

The BGP ASN report displays all three advertised prefixes:

| Node/ASN | Router ID | Advertised prefixes |
|----------|----------:|--------------------:|
| **AS65000** ||
| r1 | 10.0.0.1 | 10.0.0.1/32<br>172.16.0.0/24<br>172.16.17.0/28<br>2000:db8:cafe::/96 |

You can see the loopback interfaces **bgp.originate** creates during the **netlab create** process with the addressing report:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **r1** |  10.0.0.1/32 |  | Loopback |
| Ethernet1 | 172.16.0.1/24 |  | r1 -> stub |
| Loopback1 | 172.16.17.1/28 |  | BGP originate #1 |
| Loopback2 |  | 2000:db8:cafe::1/96 | BGP originate #2 |
