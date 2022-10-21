# First-Hop Gateway Configuration Module

First-hop Gateway configuration module implements mechanisms used to implement a shared router IPv4 address on a stub access network.

The current implementation of the module supports statically configured anycast gateway IPv4 address.

The module is supported on these platforms:

| Operating system      | Anycast |
| --------------------- | :-: |
| Arista EOS            | ✅  |

```{note}
* Arista's implementation of anycast gateway is called Virtual ARP
```

## Global Parameters

The module supports the following global parameters: 

* **gateway.protocol** (default: *anycast*) -- the first-hop gateway resolution protocol. The only supported value is currently *anycast*
* **gateway.id** (default: -1) -- the IP address within the subnet used for the gateway IP address

Anycast implementation of shared first-hop IP address supports these parameters:

* **gateway.anycast.unicast** (default: True) -- configure node-specific unicast IP addresses together with anycast IP address.
* **gateway.anycast.mac** -- Static MAC address used for the anycast IP address

```{tip}
Many implementations require unique unicast IP addresses configured on the interfaces that have anycast IP address. Set **‌gateway.anycast.unicast** to *‌False* only when absolutely necessary.
```

## Link Parameters

Gateway configuration module is enabled on all links that have **gateway** attribute set to *True* or to a dictionary of valid parameters. You can change most global parameters on per-link basis[^MAC].

[^MAC]: Some platforms don't support per-link *virtual router MAC address*, so it might not be a good idea to set **gateway.anycast.mac** parameter on individual links.
