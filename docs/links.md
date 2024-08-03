(topo-links)=
# Links between Network Devices

Links between virtual lab devices are specified in the **links** element of the topology file -- a list of links in one of these formats:

* A dictionary of node names and other link attributes. Use this format when you want to have tight control over interface attributes like IP addresses or when you have to specify additional link attributes like OSPF cost.
* A list of node names. Use this format for multi-access interface when you're OK with default IP addressing and don't need to specify additional link attributes.
* A string in *node*-*node* format. Use this format for a point-to-point link.
* A dictionary of link attributes and a list of node interfaces.

You can use all four link formats in the same topology file; they are always converted into a dictionary+list of interfaces format and augmented with addressing details during the [topology transformation process](dev/transform.md).

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
```

(link-formats)=
## Sample Link Formats

The following simple topology file contains typical link format variants. For more details, read the extensive [link definition examples](example/link-definition.md)

```
---
defaults:
  device: iosv

nodes:
- r1
- r2
- r3

links:
- r1-r2
- [ r1, r3 ]
- r2:
  r3:
```

```{tip}
When you want to specify additional link parameters, you must use the dictionary format of the link definition.
```

(link-attributes)=
## Link Attributes

A dictionary describing an individual link contains *node names* and *additional link attributes*. These link attributes are predefined and used by *netlab* data transformation routines:

* **bandwidth** -- link bandwidth. Used to configure interface bandwidth when supported by the connected device(s).
* **bridge** -- [name of the underlying OS network (bridge)](#bridge-names) if supported by the virtualization environment
* **disable** -- remove the link from the lab topology when set to `True`. You can use this attribute to simplify the topology when debugging it[^CIN].
* **gateway** -- default gateway for hosts attached to the link. See [Hosts and Default Gateways](#hosts-and-default-gateways) for more details.
* **group** -- [link group](link-groups) identifier
* **linkindex** [R/O] -- link sequence number (starting with one), used to generate internal network names in VirtualBox and default bridge names in libvirt.
* **members** -- list of links in a [link group](link-groups)
* **mtu** -- link MTU (see [Changing MTU](#changing-mtu) section for more details)
* **name** -- link name (used for interface description)
* **pool** -- addressing pool used to assign a prefix to this link. The **pool** attribute is ignored on links with a **prefix** attribute.
* **prefix** -- [prefix (or a set of prefixes)](links-static-addressing) used on the link. Setting **prefix** to *false* will give you a link without any IP configuration[^NOIP]
* **role** -- link role selects specific configuration module behavior. Typical link roles include *stub*, *passive*, and *external*. Please read [](module/routing.md) for more details.
* **type** -- [link type](#link-types) (lan, p2p, stub, loopback, tunnel)

[^CIN]: Disabled links are removed from lab topology, which might cause changes in interface names.

You can use most link attributes on individual node attachments (dictionary under *node name* key). You can also use these node attachment attributes:

* **ifindex** -- optional per-node interface index used to generate the interface/port name. Use this parameter to select specific ports to match typical network designs (for example, high-speed ports for uplinks) when the virtualization provider supports mapping host interfaces into VM/container interfaces.
* **ifname** -- target interface name. Use to create tunnel interfaces on some platforms or to create unusual interface types.

[^NOIP]: You might need links without IP configuration to test VLANs, bridging, or EVPN.

Links could contain [additional attributes](#custom-attributes-in-link-and-interface-data) like *delay* (see [custom attributes](extend-attributes.md) for more details). Links could also contain [module-specific attributes](modules.md#module-specific-node-and-link-attributes); for more information, read the documentation of individual configuration modules.

### Example

The *[IGP metric used in BGP route selection](https://github.com/ipspace/netlab-examples/tree/master/BGP/IGP-metric)* scenario uses the following topology file to define link bandwidth on a backup link:

```
defaults:
  device: iosv

nodes:
- name: e1
  module: [ isis,ospf ]
- name: e2
  module: [ isis ]
- name: pe1
  device: nxos
  module: [ isis,ospf ]

links:
- pe1:
  e1:
- pe1:
  e2:
  bandwidth: 100000
```

## Link Types

Lab topology could contain *lan*, *p2p*, *stub*, *loopback* and *tunnel* links. The link type could be specified with the **type** attribute; when that attribute is missing the link type is selected based on the number of devices connected to the link:

* Single node connected to a link ⇒ *stub* or *loopback* (see below)
* Two nodes connected to a link ⇒ *p2p*
* More than two nodes connected to a link, or a [link with a host attached](#hosts-and-default-gateways) ⇒ *lan*

The link type influences the [address prefix pool](addressing.md) used to assign IPv4 and IPv6 prefixes to the link and the node addressing:

* Prefixes assigned to point-to-point links are taken from *p2p* pool. The node with the smaller node name gets the lower (.1) address; the other node gets the higher (.2) address. The default addressing setup uses /30 IPv4 prefixes and /64 IPv6 prefixes.
* Prefixes assigned to other links are taken from the *lan* pool unless you specified the **pool** link attribute. The host portion of the IP address on large-enough prefixes is the [node ID](nodes.md#augmenting-node-data). When faced with a non-VLAN prefix that would not accommodate the highest ID of a node connected to the link, *netlab* uses [sequential IP address allocation](addressing-tutorial-lan-links).

The default link types usually work well, and you should use the **pool** attribute to specify the address pool instead of changing the link **type**. You might have to change link **type** in advanced scenarios; for example, you must set link **type** to **lan** to use Linux bridges instead of UDP tunnels in [libvirt](labs/libvirt.md) environment.

(links-loopback)=
### Loopback Links

Stub links (links with a single node) are treated as physical links and consume VM/container interfaces. Some virtualization platforms limit the number of VM interfaces, so you might be forced to turn such links into loopback interfaces.

You could turn an interface attached to a stub link into a loopback interface with **type: loopback** link attribute. You could also change the default behavior with the `defaults.devices.<device>.features.stub_loopback` device-specific setting or set the `defaults.links.stub_loopback` global default..

For example, to turn stub links into loopbacks on Arista EOS devices, use the following setting:

```
defaults:
  devices.eos.features.stub_loopback: True
```

To turn stub links into loopback interfaces on all lab devices apart from Cisco IOSv routers, set the global default to *True* and the IOSv parameter to *False*:

```
defaults:
  links.stub_loopback: True
  devices.iosv.features.stub_loopback: False
```

(links-tunnel)=
### Tunnel Links

Links with **type: tunnel** can be used to create tunnel interfaces. Tunnel links are addressed like LAN links and can have any valid link/module attribute.

_netlab_ assigns an IP prefix to the tunnel link, creates tunnel interfaces on nodes connected to tunnel links, assigns IP addresses to the tunnel interfaces, and copies all other link parameters into interface data. The tunnel interface name is generated from device data (when available) or specified in the **ifname** interface (node-on-link) parameter.

Standard _netlab_ device configuration templates will create tunnel interfaces and configure all _netlab_-supported parameters. You must use custom configuration templates to configure tunnel-technology-specific parameters (for example, source and destination underlay IP address and tunnel encapsulation).

For example, this topology creates a tunnel between two Cisco CSR edge routers.

```
defaults.device: csr
nodes: [ r1, r2, r3 ]
links:
- r1-r2
- r2-r3
- r1:
  r3:
    ifname: Tunnel42
  type: tunnel
```

**Notes:**

* **r1** will get tunnel interface `Tunnel0` (Cisco CSR device data contains tunnel interface name template)
* The tunnel on **r2** will be named `Tunnel42` due to **ifname** parameter.

## Link Names

Each link could have a **name** attribute. That attribute is copied into interface data and used to set interface **description**. Interfaces connected to links with no **name** attribute get default names as follows:

* Interfaces connected to P2P links: `R1 -> R2`
* Interfaces connected to LAN links: `R1 -> [R2,R3,R4]`
* There is no default name for stub interfaces/links.

### Example

Given this topology...

```
nodes:
- r1
- r2
- r3

links:
- r1-r2
- [ r1, r2, r3 ]
- r1:
  r2:
  name: P2P link
- r1:
  r2:
  r3:
  name: LAN link
```

... interfaces on **r1** get the following names:

1. `r1 -> r2`
2. `r1 -> [r2,r3]`
3. `P2P link`
4. `LAN link`

(link-groups)=
## Link Groups

When your lab topology contains numerous links with identical (or similar) attributes, it might be worth defining those links as a *link group*. A link group MUST have a **group** attribute (an *identifier*) and a list of **member** links.

The link initialization phase of the lab topology transformation creates new regular links from the group **member** links. Group attributes (apart from **group** and **members**) are added to the member link attributes.

You could, for example, use a link group to define a set of links with the same VLANs in a VLAN trunk ([complete example](https://github.com/ipspace/netlab-examples/tree/master/VRF/multihop-vrf-lite)):

```
links:
- group: core_trunks
  vlan.trunk: [ red, blue ]
  members: [ s1-s2, s2-s3, s1-s3 ]
```

(links-static-addressing)=
## Static Link Addressing

You can use the **prefix** attribute to specify the IPv4 and/or IPv6 prefix to be used on the link. When the **prefix** attribute is not specified, the link prefix is taken from the corresponding address pool ([see above](#link-types)).

The **prefix** attribute could be an IPv4 CIDR prefix or a dictionary with **ipv4**, **ipv6**, and **[allocation](addr-allocation)** elements.

You can use the shorthand (string) syntax if you're building an IPv4-only network, for example:

```
- name: Link with static IPv4 prefix
	e2:
  pe1:
  type: lan
  prefix: 192.168.22.0/24
```

In dual-stack or IPv6-only environments you have to use the prefix dictionary syntax:

```
- name: IPv6-only link
	e1:
  pe1:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
- name: Dual-stack link
	e1:
  e2:
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
```

### Links Without Explicit Network-Layer Addresses

* To create a layer-2-only link, set **prefix** to *False*.
* To create unnumbered link, set **unnumbered** link attribute to *True*
* To enable IPv4 or IPv6 processing on interfaces attached to the link without assigning IP addresses to those interfaces, set the **ipv4** or **ipv6** prefix attribute to **True**.

## Static Interface Addressing

You can specify a static interface address within the link-specific node data with the **ipv4** and/or **ipv6** attributes. You can also set **ipv4** or **ipv6** attribute of link-specific node data to these special values:

* *True*: enable IPv4 or IPv6 on the interface without assigning it an IP address (unnumbered/LLA-only interface)
* *False*: disable IPv4 or IPv6 on the interface, allowing you to have layer-2-only nodes attached to an IPv4/IPv6 subnet (needed to implement stretched subnets).
* *an integer value*: the interface is assigned N-th IPv4/IPv6 address from the link prefix.

The following example uses static interface addresses for two out of three nodes connected to a LAN link:

```
- e2:
    ipv4: 192.168.22.17
  e1:
    ipv4: 10.42.0.2/29
  e3:
  prefix: 192.168.22.0/24
```

These interface addresses are assigned to the three nodes during the topology transformation process:

* e1: 10.42.0.2/29 (unchanged)
* e2: 192.168.22.17/24 (subnet mask copied from on-link prefix)
* e3: 192.168.22.3/24 (IPv4 address derived from on-link prefix and node **id**).

**Caveats**

* An interface address could use a subnet mask that does not match the link subnet mask[^smm]. If you don't specify a subnet mask in an interface address, it's copied from the link prefix.
* You could specify an IPv6 interface address on an IPv4-only link (or vice versa). An interface address belonging to an address family not specified in the link prefix (static or derived from an address pool) is not checked.

[^smm]: Not recommended for obvious reasons, but you could do it.

## Selecting Custom Address Pools

The address pool used to generate IPv4 and IPv6 prefixes for a link is selected based on link type ([see above](#link-types), also *[Address Pool Overview](addressing.md)*).

Use the **pool** attribute to specify a custom address pool for a link. For example, the following topology uses an unnumbered (core) link between **r1** and **r2**:

```
addressing:
  core:
    unnumbered: true

nodes:
- r1
- r2

links:
- r1:
  r2:
  pool: core
```

```{tip}
You can also use the **unnumbered** link attribute to get a single unnumbered link. Using an unnumbered pool is recommended when testing network-wide addressing changes.
```

## Changing MTU

All devices supported by *netlab* are assumed to use ancient default layer-3 MTU value of 1500 bytes. Most VM-based network devices already use that default; container-based devices have their MTU set to 1500 through system settings.

Please note that the **mtu** specified by *netlab* is always the layer-3 (IPv4 or IPv6) MTU. The peculiarities of individual device configuration commands are transparently (to the end-user) handled in the device configuration templates.

You can change the **mtu** on an individual interface (probably not a good idea), on a link, for a particular node, device type, or the whole lab.

### Interface MTU

To change interface **mtu**, set the **mtu** parameter of a single node attached to a link. For example, if you want to prove that MTU changes break the OSPF adjacency process, use this setup:

```
links:
- r1:
    mtu: 1504
  r2:
```

### Link MTU

**mtu** parameter applied to a link is copied into interface data of all interfaces attached to that link (ensuring OSPF still works):

```
links:
- r1:
  r2:
  mtu: 1504
```

### Node MTU

**mtu** parameter specified on a node is applied to all node interfaces without MTU set through a link or interface parameter. In the following example, r1 has **mtu** set to 1500 bytes on the inter-router link and to **8192** bytes on the stub link:

```
nodes:
  r1:
    mtu: 8192
  r2:
links:
- r1:
- r1:
  r2:
  mtu: 1500
```

When the node **mtu** parameter is not specified, its default value is fetched from **defaults.interfaces.mtu** or **defaults.devices** setting.

For example, to build a lab using 8K jumbo frames, use:

```
defaults.interfaces.mtu: 8192
```

All devices without explicit MTU setting will inherit the lab-wide default (8192), which will be further propagated to all interfaces without an explicit MTU value.

**mtu** parameter can also be specified within device defaults. For example, to set the default Cumulus Linux MTU to 1500, use:

```
defaults.devices.cumulus.mtu: 1500
```

### Lab-wide MTU

The **defaults.interfaces.mtu** setting specifies the lab-wide default MTU value. If needed, you can change that value with the node, link, or interface **mtu** parameter.

## Hosts and Default Gateways

A lab device could be a networking device or a host[^HOST]. Links with attached hosts are treated slightly differently than the regular links:

* The link type is set to **lan** regardless of the number of nodes attached to it.
* If the link **role** is not defined in the topology file, it's set to **stub**  to turn the attached router interfaces into *passive* interfaces[^NOPASS].
* If the link **gateway** attribute is not defined, it's set to the IP address of the first attached non-host device. You can set the link **gateway** to any value you wish; the value is not checked.
* The link **gateway** attribute is copied into the interface data of host nodes and is used to create static routes pointing to the default gateway during the initial device configuration.

[^HOST]: Host devices are identified by **role: host** node attribute. **linux** is the only built-in host device available at the moment.

[^NOPASS]: To turn a link with hosts attached into a transit link, set link **role** to **lan** (or any other role).

## Bridge Names

Point-to-point links between network devices are implemented with P2P tunnels (assuming the virtualization environment supports them).

Multi-access and stub links are implemented with custom networks (as supported by the underlying virtualization environment). The **bridge** attribute allows you to specify the custom network name; its default value is *name_N* where:

* *name* is the [topology name](topology-overview.md) or current directory name;
* *N* is the link ID (position of link object in **links** list) starting with 1.

## Augmenting Link Data

The *netlab* data transformation code heavily augments link and corresponding node data. The additional link attributes include:

* Global link index
* Interface index for each of the attached nodes
* Link IPv4 and/or IPv6 prefix
* IPv4 and/or IPv6 addresses of attached nodes

### Examples

Point-to-point link data from a lab topology file:

```
- r1-r2
```

Final link data:

```
- interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.1/30
    node: r1
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.2/30
    node: r2
  linkindex: 1
  node_count: 2
  prefix:
    ipv4: 10.1.0.0/30
  type: p2p
```

IPv6-only point-to-point link:

```
- r1:
  r2:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
```

Final link data:

```
- interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv6: 2001:db8:cafe:1::1/64
    node: r1
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv6: 2001:db8:cafe:1::2/64
    node: r2
  linkindex: 1
  node_count: 2
  prefix:
    ipv6: 2001:db8:cafe:1::/64
  type: p2p
```

LAN link with two nodes attached to it:

```
- r1:
  r2:
  type: lan
```

Final link data:

```
- bridge: X_1
  interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 172.16.0.1/24
    node: r1
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 172.16.0.2/24
    node: r2
  linkindex: 1
  node_count: 2
  prefix:
    ipv4: 172.16.0.0/24
  type: lan
```

## Augmenting Node Data

Link processing code adds link (interface) data to all nodes connected to links. The link data is created as **interfaces** dictionary within the node data and includes:

* Interface index
* Interface name (derived from device data)
* IPv4 and/or IPv6 addressing
* Neighbor information (node name, remote interface name, remote IPv4/IPv6 address)
* Remote node ID and interface ID for point-to-point links

### Examples

A simple 3-router lab with a triangle of links can be described with this topology file:

```
nodes: [ r1, r2, r3 ]

links:
- r1-r2
- r1:
  r3:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
- r2:
    ifindex: 10
  r3:
    ifindex: 12
  type: lan
```

R1 is connected to two point-to-point links, and the **interfaces** dictionary in R1 describes two P2P interfaces (other node attributes are explained in [network nodes](nodes.md) document):

```
r1:
  af:
    ipv4: true
    ipv6: true
  box: cisco/iosv
  device: iosv
  id: 1
  interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.1/30
    linkindex: 1
    name: r1 -> r2
    neighbors:
    - ifname: GigabitEthernet0/1
      ipv4: 10.1.0.2/30
      node: r2
    type: p2p
  - ifindex: 2
    ifname: GigabitEthernet0/2
    ipv6: 2001:db8:cafe:1::1/64
    linkindex: 2
    name: r1 -> r3
    neighbors:
    - ifname: GigabitEthernet0/1
      ipv6: 2001:db8:cafe:1::2/64
      node: r3
    type: p2p
  loopback:
    ifindex: 0
    ifname: Loopback0
    ipv4: 10.0.0.1/32
    neighbors: []
    type: loopback
    virtual_interface: true
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.101
    mac: 08:4f:a9:00:00:01
  name: r1
```

R2 is connected to a P2P link (with R1) and a LAN link (forced with **type: lan** attribute). R2 node data contains the following interface data:

```
r2:
  af:
    ipv4: true
  box: cisco/iosv
  device: iosv
  id: 2
  interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.2/30
    linkindex: 1
    name: r2 -> r1
    neighbors:
    - ifname: GigabitEthernet0/1
      ipv4: 10.1.0.1/30
      node: r1
    type: p2p
  - bridge: X_3
    ifindex: 10
    ifname: GigabitEthernet0/10
    ipv4: 172.16.0.2/24
    linkindex: 3
    name: r2 -> r3
    neighbors:
    - ifname: GigabitEthernet0/12
      ipv4: 172.16.0.3/24
      node: r3
    type: lan
  loopback:
    ifindex: 0
    ifname: Loopback0
    ipv4: 10.0.0.2/32
    neighbors: []
    type: loopback
    virtual_interface: true
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.102
    mac: 08:4f:a9:00:00:02
  name: r2
```

Note the differences between P2P and LAN links:

* IPv4 subnet mask: when using default settings, P2P links use the **p2p** address pool (default: /30 prefixes), LAN links use the **lan** address pool (default: /24 prefixes)
* **bridge** name is present in LAN links

## Custom Attributes in Link and Interface Data

Additional link attributes (including [custom attributes](extend-attributes.md)) specified in the link data are copied directly into the node interface data. For example, in this simple topology, we specified **bandwidth** on a link between R1 and R2:

```
nodes: [ r1, r2 ]

links:
- r1:
  r2:
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
  bandwidth: 100000
```

Bandwidth parameter is retained in link data:

```
- bandwidth: 100000
  interfaces:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    node: r1
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 192.168.23.2/24
    ipv6: 2001:db8:cafe:2::2/64
    node: r2
  linkindex: 1
  node_count: 2
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
  type: p2p
```

The same parameter is also copied into interface data on R1 and R2:

```
r1:
  af:
    ipv4: true
    ipv6: true
  box: cisco/iosv
  device: iosv
  id: 1
  interfaces:
  - bandwidth: 100000
    ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    linkindex: 1
    name: r1 -> r2
    neighbors:
    - ifname: GigabitEthernet0/1
      ipv4: 192.168.23.2/24
      ipv6: 2001:db8:cafe:2::2/64
      node: r2
    type: p2p
...
```

```eval_rst
.. toctree::
   :caption: Detailed Examples
   :maxdepth: 1

   example/link-definition.md
   example/addressing-tutorial.md
```
