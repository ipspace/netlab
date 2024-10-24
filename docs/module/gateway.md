# First-Hop Gateway Configuration Module

The first-hop Gateway configuration module implements mechanisms used to implement a shared router IPv4 address on a stub access network.

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
| FRRouting             | ✅  | ✅  | ✅  |
| Nokia SR OS           | ✅  | ✅  | ✅  |
| Nokia SR Linux        | ✅  | ❌  | ❌  |
| VyOS                  | ❌  | ✅  | ✅  |

## Global Parameters

The module supports the following global parameters:

* **gateway.protocol** (default: *anycast*) -- the first-hop gateway resolution protocol. The supported values are *anycast* and *vrrp*.
* **gateway.id** (default: -2) -- the IP address within the subnet used for the gateway IP address. The **gateway.id** could be a positive number (a fixed IP address within a subnet using the *gateway* module) or a negative number specifying the offset from the end of the subnet. The default value specifies a subnet's last valid IP address (-1 is the broadcast address).

## Link Parameters

The Gateway configuration module is enabled on all links that have the **gateway** attribute set to *True* or to a dictionary of valid parameters. You can change most global parameters on a per-link basis.

## Interface Parameters

You can specify **gateway: True** or a dictionary of valid parameters on [individual interfaces](link-interface-attribute) (nodes-on-a-link data).

Specifying a **gateway** interface attribute on a link that does not have a **gateway** attribute automatically enables the Gateway configuration module on the connected link but turns it off for other nodes connected to the same link, ensuring the Gateway module is active only on the nodes where you explicitly enabled it.

Similarly, you can use the **gateway: False** setting to turn off the default gateway functionality on individual interfaces on a link on which the Gateway configuration module is enabled.

## Reserved IP Addresses

A positive **gateway.id** value could generate IP addresses that overlap with node interface addresses on subnets using [ID-based address allocation](addr-allocation).

The *gateway* module tries to prevent that and reserves the node ID values specified in the global, link, or global VLAN **gateway.id** values.

```{tip}
If you want to use one of the first IP addresses in the high-availability subnets as the gateway IP address, set the global value of the **‌gateway.id** parameter unless you have an excellent reason to do something else.
```

## Anycast Gateway

The *gateway* configuration module supports IPv4 anycast gateways, which use MAC and IPv4 addresses shared between multiple nodes attached to the same segment.

### Implementation Notes

* The default *netlab* shared MAC address is 0200.cafe.00ff.
* The gateway IP is configured to respond to ping requests
* Vendors use different names for anycast gateways: VARP (Arista), VRR (Cumulus), passive VRRP (Nokia)
* Arista EOS uses the same shared MAC address on all interfaces. Do not set the link-level **gateway.anycast.mac** parameter in topologies using Arista EOS.
* Arista vEOS cannot use VRRP MAC address as a shared MAC address (default recommended by Cumulus Linux)

### Anycast Parameters

Anycast implementation of shared first-hop IPv4 address supports these parameters that can be specified globally or on individual links or interfaces.

* **gateway.anycast.unicast** (default: True) -- configure node-specific unicast IP addresses even when using the anycast IP address.
* **gateway.anycast.mac** -- Static MAC address used for the anycast IPv4 address

```{tip}
* Many implementations require unique unicast IPv4 addresses configured on interfaces with anycast IPv4 address. Set **gateway.anycast.unicast** to *False* only when absolutely necessary.
```

## Virtual Router Redundancy Protocol (VRRP)

*netlab* supports a single VRRPv3 instance per subnet/interface. The VRRPv3 instance can provide shared IPv4 and IPv6 addresses.

```{tip}
More complex topologies, such as multiple VRRPv3 instances *on the same subnet*, could be deployed with a judicious application of interface parameters[^VNS]. Still, you won't be able to model multiple VRRPv3 instances *per interface*[^VDM].
```

[^VNS]: These topologies are unsupported and will not be integrated into the *netlab* core. If you want an easier way of configuring them in a lab topology, please feel free to create a plugin.

[^VDM]: That would require a completely different data model. You'll have to use custom configuration templates to implement something along those lines.

### VRRP Parameters

*netlab* supports these VRRP parameters that can be specified globally or on individual nodes, links, or interfaces.

* **vrrp.group** (default: 1) -- VRRP group
* **vrrp.priority** (interface parameter, integer)
* **vrrp.preempt** (interface parameter, boolean) -- VRRP preempting is enabled by default; you can disable it with **vrrp.preempt: False**.

No other aspect of VRRP (VRRP version, timers...) is manageable through *netlab* parameters; if you want to configure them, create a plugin to implement additional VRRP functionality.
