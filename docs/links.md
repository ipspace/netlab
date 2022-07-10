# Links between Network Devices

Links between virtual lab devices are specified in **links** element of the topology file -- a list of links in one of these formats:

* A dictionary of node names and other link attributes. Use this format when you want to have a tight control over interface attributes like IP addresses, or when you have to specify additional link attributes like OSPF cost.
* A list of node names. Use this format for multi-access interface when you're OK with default IP addressing and don't need to specify any additional link attributes.
* A string in *node*-*node* format. Use this format for a point-to-point link.
* A dictionary of link attributes and a list of node interfaces.

You can use all four link formats in the same topology file -- they are always converted into a dictionary+list of interfaces format, and augmented with addressing details during the [topology transformation process](dev/transform.md).

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
```

## Sample Link Formats

The following simple topology file contains typical variants of specifying nodes connected to a link. For more details, read the extensive [link definition examples](example/link-definition.md)

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

**Note:** You have to use the dictionary format of link definition when you want to specify additional link parameters.

## Link Attributes

A dictionary describing an individual link contains *node names* as well as *additional link attributes*. These link attributes are predefined and used by *netsim-tools* data transformation routines:

* **prefix** -- [prefix (or a set of prefixes)](#static-link-addressing) used on the link. Setting **prefix** to *false* will give you a link without any IP configuration[^NOIP]
* **type** -- [link type](#link-types) (lan, p2p, stub)
* **bridge** -- [name of the underlying OS network (bridge)](#bridge-names) if supported by the virtualization environment
* **linkindex** [R/O] -- link sequence number (starting with one), used to generate internal network names in VirtualBox and default bridge names in libvirt.
* **name** -- link name (used for interface description)
* **role** -- link role, used to select custom addressing pool or specific configuration module behavior.
* **bandwidth** -- link bandwidth (used to configure interface bandwidth).
* **mtu** -- link MTU (see [Changing MTU](#changing-mtu) section for more details)
* **gateway** -- default gateway for hosts attached to the link. See [Hosts and Default Gateways](#hosts-and-default-gateways) for more details.

You can use all link attributes on individual node attachments (dictionary under *node name* key). You can also use these node attachment attributes:

* **ifindex** -- optional per-node interface index used to generate the interface/port name. Useful to select specific ports to match typical network designs (example: using high-speed ports for uplinks).

[^NOIP]: You might need links without IP configuration if you want to test VLANs, bridging, or EVPN.

Links could contain [additional attributes](#custom-attributes-in-link-and-interface-data) like *delay* (see [custom attributes](extend-attributes.md) for more details). Links could also contain [module-specific attributes](modules.md#module-specific-node-and-link-attributes); for details read the documentation of individual configuration modules.

### Example

The *[IGP metric used in BGP route selection](https://github.com/ipspace/netsim-examples/tree/master/BGP/IGP-metric)* scenario uses the following topology file to define link bandwidth on a backup link (*bandwidth* became a core link attribute in release 0.4):

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

Lab topology could contain *stub*, *p2p* and *lan* links. The link type could be specified with the **type** attribute; when that attribute is missing the link type is selected based on the number of devices connected to the link:

* Single node connected to a link ⇒ *stub*
* Two nodes connected to a link ⇒ *p2p*
* More than two nodes connected to a link, or a [link with a host attached](#hosts-and-default-gateways) ⇒ *lan*

The link type influences the [address prefix pool](addressing.md) used to assign IPv4 and IPv6 prefixes to the link and the node addressing:

* Prefixes assigned to point-to-point links are taken from *p2p* pool. The node with the smaller node name gets the lower (.1) address, the other node gets the higher (.2) address. The default addressing setup uses /30 IPv4 prefixes and /64 IPv6 prefixes.
* Prefixes assigned to multi-access (LAN) links are taken from *lan* pool. The host portion of the IP address is the [node ID](nodes.md#augmenting-node-data)
* Stub links are treated exactly like LAN links.

## Link Names

Each link could have a **name** attribute that is copied into interface data and used to set interface **description**. Interfaces connected to links with no **name** attribute get default names as follows:

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

## Static Link Addressing

You can use the **prefix** attribute to specify IPv4 and/or IPv6 prefix to be used on the link. When the **prefix** attribute is not specified, the link prefix is taken from the corresponding address pool ([see above](#link-types)).

The **prefix** attribute could be either an IPv4 CIDR prefix or a dictionary with **ipv4** and/or **ipv6** elements.

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

### Other Link Types

* To create a layer-2-only link, set **prefix** to *False*.
* To create unnumbered link, set **unnumbered** link attribute to *True*
* To enable IPv4 or IPv6 processing on interfaces attached to the link without assigning IP addresses to those interfaces, set **ipv4** or **ipv6** prefix attribute to **True**.

## Static Interface Addressing

You can specify static interface address with the **ipv4** and/or **ipv6** attributes within the link-specific node data. You can also set **ipv4** or **ipv6** attribute of link-specific node data to these special values:

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

These interface address are assigned to the three nodes during the topology transformation process:

* e1: 10.42.0.2/29 (unchanged)
* e2: 192.168.22.17/24 (subnet mask copied from on-link prefix)
* e3: 192.168.22.3/24 (IPv4 address derived from on-link prefix and node **id**).

**Caveats**

* An interface address could use a subnet mask that does not match the link subnet mask[^smm]. If you don't specify a subnet mask in an interface address, it's copied from the link prefix.
* You could specify an IPv6 interface address on an IPv4-only link (or vice versa). An interface address belonging to an address family that is not specified in the link prefix (static or derived from an address pool) is not checked.

[^smm]: Not recommended for obvious reasons, but you could do it.

## Selecting Custom Address Pools

The address pool used to generate IPv4 and IPv6 prefixes for a link is selected based on link type ([see above](#link-types), also *[Address Pool Overview](addressing.md)*).

Use **role** attribute to specify a custom address pool for a link. For example, the following topology uses unnumbered (core) link between **r1** and **r2**:

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
  role: core
```

**Notes:**

* The name used in **role** attribute does not have to correspond to an IP address pool. In that case, the address pool is selected based on link type.
* Link **role** could be used in [configuration modules](modules.md) to influence interface configuration. For example, *core* links could belong to OSPF area 0.

```{tip}
You can also use **‌unnumbered** link attribute to get a single unnumbered link. Using an unnumbered pool is recommended when you want to test network-wide addressing changes.
```

## Changing MTU

All devices supported by *netsim-tools* are assumed to use ancient default layer-3 MTU value of 1500 bytes. Most VM-based network devices already use that default; container-based devices have their MTU set to 1500 through system settings.

Please note that the **mtu** specified by *netsim-tools* is always the layer-3 (IPv4 or IPv6) MTU. The peculiarities of individual device configuration commands are transparently (to the end-user) handled in the device configuration templates.

You can change the **mtu** on an individual interface (probably not a good idea), on a link, for a particular node or device type, or for the whole lab.

### Interface MTU

To change interface **mtu**, set the **mtu** parameter of a single node attached to a link. For example, if you want to prove that MTU changes break OSPF adjacency process, use this setup:

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

**mtu** parameter specified on a node is applied to all node interfaces that don't have their MTU set through a link or interface parameter. In the following example, r1 has **mtu** set to 1500 bytes on the inter-router link and to **8192** bytes on the stub link:

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

All devices without explicit MTU setting will inherit the lab-wide default (8192) which will be further propagated to all interfaces without an explicit MTU value.

**mtu** parameter can also be specified within device defaults. For example, to set default Cumulus Linux MTU to 1500 use:

```
defaults.devices.cumulus.mtu: 1500
```

### Lab-wide MTU

Lab-wide MTU is specified with  setting and *overrides node or device defaults*. You can still specify different MTU on individual links or interfaces.

## Hosts and Default Gateways

A lab device could be a network device or a host[^HOST]. Links with attached hosts are treated slightly differently than the regular links:

* Link **type** is set to **lan** regardless of the number of nodes attached to the link.
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

Link data and corresponding node data are heavily augmented by the *netsim-tools* data transformation code. The additional link attributes include:

* Global link ID
* Link index for each of the attached nodes
* Link IPv4 and/or IPv6 prefix
* IPv4 and/or IPv6 addresses of attached nodes
* Link name (for P2P links)
* **left** and **right** node on a P2P link

### Examples

Point-to-point link data from topology file:

```
- r1-r2
```

Final link data:

```
- interfaces:
  - ipv4: 10.1.0.1/30
    node: r1
  - ipv4: 10.1.0.2/30
    node: r2
  left:
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.1/30
    node: r1
  linkindex: 1
  name: r1 - r2
  node_count: 2
  prefix:
    ipv4: 10.1.0.0/30
  right:
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.2/30
    node: r2
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
  - ipv6: 2001:db8:cafe:1::1/64
    node: r1
  - ipv6: 2001:db8:cafe:1::2/64
    node: r2
  left:
    ifname: GigabitEthernet0/2
    ipv6: 2001:db8:cafe:1::1/64
    node: r1
  linkindex: 2
  name: r1 - r2
  node_count: 2
  prefix:
    ipv6: 2001:db8:cafe:1::/64
  right:
    ifname: GigabitEthernet0/2
    ipv6: 2001:db8:cafe:1::2/64
    node: r2
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
- bridge: X_3
  interfaces:
  - ipv4: 172.16.0.1/24
    node: r1
  - ipv4: 172.16.0.2/24
    node: r2
  linkindex: 3
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
    remote_id: 2
    remote_ifindex: 1
    type: p2p
  - ifindex: 10
    ifname: GigabitEthernet0/10
    ipv6: 2001:db8:cafe:1::1/64
    linkindex: 2
    name: r1 -> r3
    neighbors:
    - ifname: GigabitEthernet0/12
      ipv6: 2001:db8:cafe:1::2/64
      node: r3
    remote_id: 3
    remote_ifindex: 12
    type: p2p
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
  name: r1
```

R2 is connected to a P2P link (with R1) and a LAN link (forced with **type: lan** attribute). R2 node data contains the following interface data:

```
r2:
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
    remote_id: 1
    remote_ifindex: 1
    type: p2p
  - bridge: X_3
    ifindex: 12
    ifname: GigabitEthernet0/12
    ipv4: 172.16.0.2/24
    linkindex: 3
    name: r2 -> [r3]
    neighbors:
    - ifname: GigabitEthernet0/10
      ipv4: 172.16.0.3/24
      node: r3
    type: lan
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
  name: r2
```

Note the differences between P2P and LAN links:

* Different auto-generated link link **name**
* IPv4 subnet mask: when using default settings, P2P links use /30 prefixes, LAN links use /24 prefixes
* **bridge** name is present in LAN links

## Custom Attributes in Link and Interface Data

[Custom attributes](extend-attributes.md) specified in link data are copied directly into node interface data. For example, in this simple topology, we specified **bandwidth** on a link between R1 and R2:

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
  - ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    node: r1
  - ipv4: 192.168.23.2/24
    ipv6: 2001:db8:cafe:2::2/64
    node: r2
  left:
    ifname: GigabitEthernet0/1
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    node: r1
  linkindex: 1
  name: r1 - r2
  node_count: 2
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
  right:
    ifname: GigabitEthernet0/1
    ipv4: 192.168.23.2/24
    ipv6: 2001:db8:cafe:2::2/64
    node: r2
  type: p2p
```

The same parameter is also copied into interface data on R1 and R2:

```
r1:
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
    remote_id: 2
    remote_ifindex: 1
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
