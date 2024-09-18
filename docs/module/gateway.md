# First-Hop Gateway Configuration Module

First-hop Gateway configuration module implements mechanisms used to implement a shared router IPv4 address on a stub access network.

The module supports statically configured anycast gateway IPv4 address and VRRPv3 for IPv4 and IPv6.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The module is supported on these platforms:

| Operating system      | Anycast | VRRPv3 | VRRPv3<br>IPv6 |
| --------------------- | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  | ✅  | ✅  |
| Cisco Catalyst 8000v  |  ❌  | ✅  | ✅  |
| Cisco CSR 1000v       |  ❌  | ✅  | ✅  |
| Cisco IOSv/IOSvL2     |  ❌  | ✅  | ✅  |
| Cisco Nexus OS        |  ❌  | ✅  | ✅  |
| Cumulus Linux         | ✅  | ✅  | ✅  |
| Dell OS10             | ✅ [❗](caveats-os10) | ✅ [❗](caveats-os10) | ✅ [❗](caveats-os10)  |
| FRRouting             | ❌   | ✅  | ✅  |
| Nokia SR OS           | ✅  | ✅  | ✅  |
| Nokia SR Linux        | ✅  | ❌  | ❌  |
| VyOS                  | ❌  | ✅  | ✅  |

## Global Parameters

The module supports the following global parameters:

* **gateway.protocol** (default: *anycast*) -- the first-hop gateway resolution protocol. The supported values are *anycast* and *vrrp*.
* **gateway.id** (default: -1) -- the IP address within the subnet used for the gateway IP address

## Link Parameters

Gateway configuration module is enabled on all links that have **gateway** attribute set to *True* or to a dictionary of valid parameters. You can change most global parameters on per-link basis.

## Anycast Gateway

The *gateway* configuration module supports IPv4 anycast gateways -- MAC and IPv4 addresses shared between multiple nodes attached to the same segment.

### Implementation Notes

* The default *netlab* shared MAC address is 0200.cafe.00ff.
* The gateway IP is configured to respond to ping requests
* Vendors use different names for anycast gateways: VARP (Arista), VRR (Cumulus), passive VRRP (Nokia)
* Arista EOS uses the same shared MAC address on all interfaces. Do not set link-level **gateway.anycast.mac** parameter in topologies using Arista EOS.
* Arista vEOS cannot use VRRP MAC address as a shared MAC address (default recommended by Cumulus Linux)

### Anycast Parameters

Anycast implementation of shared first-hop IPv4 address supports these parameters that can be specified globally or on individual links or interfaces.

* **gateway.anycast.unicast** (default: True) -- configure node-specific unicast IP addresses together with anycast IP address.
* **gateway.anycast.mac** -- Static MAC address used for the anycast IPv4 address

```{tip}
Many implementations require unique unicast IPv4 addresses configured on the interfaces that have anycast IPv4 address. Set **gateway.anycast.unicast** to *False* only when absolutely necessary.
```

## Virtual Router Redundancy Protocol (VRRP)

*netlab* supports a single VRRPv3 instance per subnet/interface. The VRRPv3 instance can provide shared IPv4 and IPv6 addresses.

```{tip}
More complex topologies like multiple VRRPv3 instances *on the same subnet* could be deployed with a judicious application of interface parameters[^VNS], but you won't be able to model multiple VRRPv3 instances *per interface*[^VDM].
```

[^VNS]: These topologies are not supported and will not be integrated into *netlab* core. If you want to have an easier way of configuring them in a lab topology, please feel free to create a plugin.

[^VDM]: That would require a completely different data model. You'll have to use custom configuration templates if you want to implement something along those lines.

### VRRP Parameters

*netlab* supports these VRRP parameters that can be specified globally or on individual links or interfaces.

* **vrrp.group** (default: 1) -- VRRP group
* **vrrp.priority** (interface parameter, integer)
* **vrrp.preempt** (interface parameter, boolean)

No other aspect of VRRP (VRRP version, timers...) is manageable through *netlab* parameters, if you want to configured them create a plugin to implement additional VRRP functionality.
