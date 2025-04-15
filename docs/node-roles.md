(node-router-host)=
# Routers, Host, and Bridges

_netlab_ supports three types of nodes:

* **[router](node-role-router)** -- a device performing a combination of layer-3 and (optional) layer-2 forwarding.
* **[host](node-role-host)** -- an IP host, usually using static (default) routes instead of a routing protocol
* **[bridge](node-role-bridge)** -- simple layer-2 switches (devices formerly known as *bridges*)

Most _netlab_-supported devices act as *routers*; see the [platform support tables](platform-host) for a list of devices that can act as hosts or bridges.

(node-role-router)=
## Routers and Layer-3 Switches

The defining characteristics of devices with the **router** role   (the default device role) are:

* At least one global [loopback interface](node-loopback) that can be used as the *router ID* and the control-plane endpoint
* Layer-3 packet forwarding for the configured address families (IPv4/IPv6)

Routers usually run routing protocols but can also rely on static routing. When used with the **[vlan](module-vlan)** configuration module, they can also perform layer-2 packet forwarding and IRB.

(node-role-host)=
## Hosts

Hosts do not have loopback interfaces (it's easiest if they have a single interface) and use static routes toward an adjacent [default gateway](links-gateway). On devices that don't have the management VRF, Vagrant or containerlab set up the default route, and _netlab_ adds static IPv4 routes for IPv4 prefixes defined in [address pools](address-pools).

Hosts that have a management VRF (mostly network devices used as hosts) get two IPv4 default routes. Vagrant or containerlab sets up the IPv4 default route in the management VRF, and netlab adds a default route toward an adjacent router in the global routing table.

Most hosts listen to IPv6 RA messages to get the IPv6 default route. _netlab_ can add an IPv6 default route[^SRv6] on devices that do not listen to RA messages.

[^SRv6]: Or a set of static IPv6 routes for address pool prefixes on devices without a management VRF

(node-role-bridge)=
## Bridges

The **bridge** role is a thin abstraction layer on top of the [**vlan** configuration module](module-vlan), making deploying simple topologies with a single bridge connecting multiple routers or hosts easier. You can also use a **bridge** node to test failover scenarios using a familiar layer-2 device[^SD].

[^SD]: It's easier to shut down an interface on a familiar device than trying to figure out how to do that on a Linux bridge.

Do not try to build complex topologies with bridges; use the VLAN configuration module.

Bridges are simple layer-2 packet forwarding devices[^VM]. They do not have a loopback interface and might not even have a data-plane IP address. Without additional parameters, _netlab_ configures them the way non-VLAN bridges have been working for decades -- bridge interfaces do not use VLAN tagging and belong to a single layer-2 forwarding domain.

[^VM]: The node **vlan.mode** parameter for a bridge node is set to **bridge** unless it's defined in the lab topology.

You can use the **bridge** devices to implement simple small bridged segments, for example:

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

In the above topology, *netlab* assigns an IP prefix from the **lan** pool to the VLAN segment connecting the four devices ([you can change that](node-bridge-details)).

You can also connect multiple bridges into a larger bridged network. This scenario stretches the limitations of the **bridge** nodes (using the [**vlan** configuration module](module-vlan) would be better). If you decide to use it in your topology, you SHOULD define a global **br_default** VLAN (defined as **vlans.br_default** topology attribute) to share the same IP subnet across all bridges.

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

(node-bridge-details)=
### Bridge Implementation Details

_netlab_ uses the **vlan** configuration module to implement the *simple bridging* functionality -- it places all bridge interfaces without an explicit **vlan** parameter into the same access VLAN.

The VLAN configuration module needs the *default access VLAN* name and VLAN ID (tag). The default name of that VLAN is **br_default**[^BRD], and it uses VLAN tag 1[^BRID] to make the final device configuration similar to the out-of-the-box configuration of simple layer-2 switches.

You can use the node- or global VLAN definition of the **br_default** VLAN to change the parameters (for example, the IP prefix or address pool) of the LAN segment created around a **bridge** node.
 
[^BRD]: You can change the name of the default bridge VLAN with the `topology.defaults.const.bridge.default_vlan.name` parameter

[^BRID]: You can change the VLAN tag of the default bridge VLAN with the `topology.defaults.const.bridge.default_vlan.id` parameter

For more VLAN configuration- and implementation details, read the [**vlan** configuration module documentation](module-vlan).

(node-bridge-lan)=
### Implementing Multi-Access Links with Bridges

To build a LAN segment with a hub-and-spoke topology of point-to-point links attaching nodes to the bridge, you can define a multi-access link with a single bridge attached to it.

For example, you can use the following topology to create a topology equivalent to the one above; the multi-access link is expanded into a series of point-to-point links with the **br** device.

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

Each multi-access link implemented with a bridge node is a separate bridging domain. _netlab_ creates a separate VLAN with a topology-wide unique VLAN ID on the bridge node for every multi-access link and copies the link attributes into the VLAN attributes. Thus, it's safe to use the same bridge node to implement multiple multi-access links.
