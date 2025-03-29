(node-router-host)=
# Routers, Host, and Bridges

_netlab_ supports three types of nodes:

* **[router](node-role-router)** -- a device performing a combination of layer-3 and (optional) layer-2 forwarding.
* **[host](node-role-host)** -- an IP host, usually using static (default) routes instead of a routing protocol
* **[bridge](node-role-bridge)** -- simple layer-3 bridges

Most _netlab_-supported devices act as *routers*; see the [platform support tables](platform-host) for a list of devices that can act as hosts or bridges.

(node-role-router)=
## Routers and Layer-3 Switches

The defining characteristics of routers are:

* At least one global [loopback interface](node-loopback) that can be used as the *router ID* and the control-plane endpoint
* Layer-3 packet forwarding for the configured address families (IPv4/IPv6)

Routers usually run routing protocols but can also rely on static routing. When used with the **[vlan](module-vlan)** configuration module, they can also perform layer-2 packet forwarding and IRB.

(node-role-host)=
## Hosts

Hosts do not have loopback interfaces (it's easiest if they have a single interface) and use static routes toward an adjacent [default gateway](links-gateway). On devices that don't have the management VRF, Vagrant or containerlab set up the default route, and _netlab_ adds static IPv4 routes for IPv4 prefixes defined in [address pools](address-pools).

Hosts that have a management VRF (mostly network devices used as hosts) get two IPv4 default routes. Vagrant or containerlab sets up the IPv4 default route in the management VRF, and netlab adds a default route in the global VRF.

Most hosts listen to IPv6 RA messages to get the IPv6 default route. _netlab_ can add an IPv6 default route[^SRv6] on devices that do not listen to RA messages.

[^SRv6]: Or a set of static IPv6 routes for address pool prefixes on devices without a management VRF

(node-role-bridge)=
## Bridges

Bridges are simple layer-2 packet forwarding devices[^VM]. They do not have a loopback interface and might not even have a data-plane IP address.

[^VM]: The node **vlan.mode** parameter for a bridge node is set to **bridge** unless it's defined in the lab topology.

Bridges can use **vlan** parameters on interfaces to define VLAN access links or VLAN trunks. All bridge interfaces without a **vlan** parameter are configured as access VLANs for the default bridge VLAN (**br_default**[^BRD]/VLAN 1[^BRID]) (`vlan.access: br_default`)

[^BRD]: You can change the name of the default bridge VLAN with the **topology.defaults.const.default_vlan.name** parameter

[^BRID]: You can change the VLAN tag of the default bridge VLAN with the **topology.defaults.const.default_vlan.id** parameter

You can use the **bridge** devices to implement simple bridged networks, for example:

```
nodes:
	rtr:
		device: eos
	h1:
		device: linux
	h2:
		device: linux
	br:
		device: ioll2
		role: bridge

links: [ rtr-br, h1-br, h2-br ]
```

In the above topology, *netlab* assigns an IP prefix from the **lan** pool to the VLAN segment connecting the four devices. You can change the **br.vlans.br_default** VLAN definition to change the parameters of the default bridge VLAN on node **br**.

You can use a multi-access link with a single bridge attached to it instead of a series of point-to-point links. The following topology is equivalent to the one above; the multi-access link is expanded into a series of point-to-point links with the **br** device.

```
nodes:
	rtr:
		device: eos
	h1:
		device: linux
	h2:
		device: linux
	br:
		device: ioll2
		role: bridge

links: [ rtr-h1-h2-br ]
```

You can also connect multiple bridges into a larger bridged network. In this scenario, you SHOULD use a global **br_default** VLAN (defined as **vlans.br_default** topology attribute) to share the same IP subnet across all bridges.

```
nodes:
	rtr:
		device: eos
	h1:
		device: linux
	h2:
		device: linux
	br1:
		device: ioll2
		role: bridge
	br2:
		device: ioll2
		role: bridge

links: [ rtr-br1, br1-br2, h1-br2, h2-br2 ]
```

```{warning}
_netlab_ does not implement multiple independent bridge domains for the same VLAN.
```

For more VLAN configuration- and implementation details, read the [**vlan** configuration module documentation](module-vlan).