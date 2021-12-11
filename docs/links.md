# Links between Network Devices

Links between virtual lab devices are specified in **links** element of the topology file -- a list of links in one of these formats:

* A dictionary of node names and other link attributes. Use this format when you want to have a tight control over interface attributes like IP addresses, or when you have to specify additional link attributes like OSPF cost.
* A list of node names. Use this format for multi-access interface when you're OK with default IP addressing and don't need to specify any additional link attributes.
* A string in *node*-*node* format. Use this format for a point-to-point link.

You can use all three link formats in the same topology file -- they are always converted into a dictionary format first, and then augmented with addressing details.

## Link Formats Example

The following link definition contains all variants of specifying nodes connected to a link:

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

[^NOIP]: You might need links without IP configuration if you want to test VLANs, bridging, or EVPN.

Links could contain [additional attributes](#custom-attributes-in-node-and-link-data) like *delay* and [module-specific attributes](modules.md#module-specific-node-and-link-attributes). Additional (custom) attributes have to be defined in **defaults.link_attr** list to differentiate them from misspelled node names. 

### Example

The *[IGP metric used in BGP route selection](https://github.com/ipspace/netsim-examples/tree/master/BGP/IGP-metric)* scenario uses the following topology file to define link bandwidth on a backup link (*bandwidth* became a core link attribute in release 0.4):

```
defaults:
  device: iosv
  link_attr: [ bandwidth ]

nodes:
- name: e1
  igp: [ isis,ospf ]
  edge: true
- name: e2
  igp: [ isis ]
  edge: true
- name: pe1
  device: nxos
  igp: [ isis,ospf ]

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
* More than two nodes connected to a link ⇒ *lan*

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

You can use the **prefix** attribute to specify IPv4 and/or IPv6 prefix to be used on the link. When the **prefix** attribute is not specified, the link prefix is taken from the corresponding address pool ([see above](#link-types)). To create a link without any IP addressing, set **prefix** to *false*.

The **prefix** attribute could be either an IPv4 CIDR prefix or a dictionary with **ipv4** and/or **ipv6** elements.

You can use the shorthand (string) syntax if you're building an IPv4-only network, for example:

```
- e2:
  pe1:
  type: lan
  prefix: 192.168.22.0/24
```

In dual-stack or IPv6-only environments you have to use the prefix dictionary syntax:

```
- e1:
  pe1:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
- e1:
  e2:
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
```

### Static Interface Addressing

You can specify static interface address with the **ipv4** and/or **ipv6** attributes within the link-specific node data. The following example uses static interface addresses for two out of three nodes connected to a LAN link:

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

* Static interface addressing does not work on P2P links. Nodes attached to a P2P link always get the first and the second IP address from the link prefix. To use static interface addressing, set the link **type** to **lan**.
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

## Bridge Names

Point-to-point links between network devices are implemented with P2P tunnels (assuming the virtualization environment supports them).

Multi-access and stub links are implemented with custom networks (as supported by the underlying virtualization environment). The **bridge** attribute allows you to specify the custom network name; its default value is *name_N* where:

* *name* is the [topology name](topology-overview.md) or current directory name;
* *N* is the link ID (position of link object in **links** list) starting with 1.

## Augmenting Link Data

Link data and corresponding node data are heavily augmented by the *netsim-tools* data transformation code. The additional link attributes include:

* Global link ID
* Link IPv4 and/or IPv6 prefix
* IPv4 and/or IPv6 addresses of attached nodes
* Link name (for P2P links)
* **left** and **right** node on a P2P link

### Examples

Point-to-point link data from topology file:

```
- e1-e2
```

Final link data:

```
- e1:
    ipv4: 10.1.0.1/30
  e2:
    ipv4: 10.1.0.2/30
  left:
    ifname: GigabitEthernet2
    ipv4: 10.1.0.1/30
    node: e1
  linkindex: 1
  name: e1 - e2
  prefix:
    ipv4: 10.1.0.0/30
  right:
    ifname: GigabitEthernet2
    ipv4: 10.1.0.2/30
    node: e2
  type: p2p
```

IPv6-only point-to-point link:

```
- e1:
  pe1:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
```

Final link data:

```
- e1:
    ipv6: 2001:db8:cafe:1::1/64
  left:
    ifname: GigabitEthernet3
    ipv6: 2001:db8:cafe:1::1/64
    node: e1
  linkindex: 2
  name: e1 - pe1
  pe1:
    ipv6: 2001:db8:cafe:1::2/64
  prefix:
    ipv6: 2001:db8:cafe:1::/64
  right:
    ifname: GigabitEthernet2
    ipv6: 2001:db8:cafe:1::2/64
    node: pe1
  type: p2p
```

LAN link with two nodes attached to it:

```
- e2: 
  pe1: 
  type: lan
```

Final link data:

```
- bridge: tests_3
  e2:
    ipv4: 172.16.0.2/24
  linkindex: 3
  pe1:
    ipv4: 172.16.0.3/24
  prefix:
    ipv4: 172.16.0.0/24
  type: lan
```

Complete topology used to generate the example printouts:

```
defaults:
  device: iosv

nodes:
- e1
- e2
- pe1

links:
- e1-e2
- e1:
  pe1:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
- e2:
  pe1:
  type: lan
```

## Augmenting Node Data

Link processing code adds link (interface) data to all nodes connected to links. The link data is created as **links** dictionary within the node data and includes:

* Interface index
* Interface name (derived from device data)
* IPv4 and/or IPv6 addressing
* Neighbor information (node name, remote interface name, remote IPv4/IPv6 address)
* Remote node ID and interface ID for point-to-point links

### Examples

E1 is connected to two point-to-point links:

```
- e1-e2
- e1:
  pe1:
  prefix:
    ipv6: 2001:db8:cafe:1::/64
```

The **links** dictionary in E1 node data describes E1 interfaces (other node attributes are explained in [network nodes](nodes.md) document):

```
- box: cisco/iosv
  device: iosv
  id: 1
  links:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.1/30
    linkindex: 1
    name: e1 -> e2
    neighbors:
      e2:
        ifname: GigabitEthernet0/1
        ipv4: 10.1.0.2/30
    remote_id: 2
    remote_ifindex: 1
    type: p2p
  - ifindex: 2
    ifname: GigabitEthernet0/2
    ipv6: 2001:db8:cafe:1::1/64
    linkindex: 2
    name: e1 -> pe1
    neighbors:
      pe1:
        ifname: GigabitEthernet0/1
        ipv6: 2001:db8:cafe:1::2/64
    remote_id: 3
    remote_ifindex: 1
    type: p2p
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
  name: e1
```

E2 is connected to a P2P link and a LAN link:

```
links:
- e1-e2
- e2:
  pe1:
  type: lan
```

E2 node data contains the following interface data:

```
- box: cisco/iosv
  device: iosv
  id: 2
  links:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.2/30
    linkindex: 1
    name: e2 -> e1
    neighbors:
      e1:
        ifname: GigabitEthernet0/1
        ipv4: 10.1.0.1/30
    remote_id: 1
    remote_ifindex: 1
    type: p2p
  - bridge: y_3
    ifindex: 2
    ifname: GigabitEthernet0/2
    ipv4: 172.16.0.2/24
    linkindex: 3
    name: e2 -> [pe1]
    neighbors:
      pe1:
        ifname: GigabitEthernet0/2
        ipv4: 172.16.0.3/24
    type: lan
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
  name: e2
```

## Custom Attributes in Node and Link Data

Custom attributes specified in link data are retained in the link data and copied directly into node interface data.

Example: Bandwidth is specified on a link between E1 and E2:

```
- e1:
  e2:
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
  bandwidth: 100000
```

Bandwidth parameter is retained in link data:

```
- bandwidth: 100000
  e1:
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
  e2:
    ipv4: 192.168.23.2/24
    ipv6: 2001:db8:cafe:2::2/64
  index: 4
  left:
    ifname: GigabitEthernet0/3
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    node: e1
  prefix:
    ipv4: 192.168.23.0/24
    ipv6: 2001:db8:cafe:2::/64
  right:
    ifname: GigabitEthernet0/3
    ipv4: 192.168.23.2/24
    ipv6: 2001:db8:cafe:2::2/64
    node: e2
  type: p2p
```

The same parameter is also copied in interface data on E1 and E2:

```
- device: iosv
  name: e1
  id: 1
  links:
...
  - bandwidth: 100000
    ifindex: 3
    ifname: GigabitEthernet0/3
    ipv4: 192.168.23.1/24
    ipv6: 2001:db8:cafe:2::1/64
    neighbors:
      e2:
        ifname: GigabitEthernet0/3
        ipv4: 192.168.23.2/24
        ipv6: 2001:db8:cafe:2::2/64
    remote_id: 2
    remote_ifindex: 3
    type: p2p
...
```
