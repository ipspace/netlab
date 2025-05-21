(tutorial-vlan-addressing)=
# VLAN Segment and Interface Addressing

VLANs are one of the more confusing aspects of any network design and configuration, and _netlab_ is no exception. There are numerous tutorials describing the [typical VLAN and VRF topologies](tutorials-vlan-vrf); this one focuses on VLAN segment and interface addressing.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(tutorial-vlan-addressing-types)=
## VLAN Types

You can use the [_netlab_ VLAN module](module-vlan) to create:

* VLAN segments, where a single VLAN connects multiple switches and attached end-nodes. This is the default behavior.
* Transport VLAN, where VLANs are used to create multiple subnets on a single link between switches or routers to implement topologies like VRF Lite.

The VLAN type is controlled by the VLAN **[mode](vlan-forwarding-modes)** parameter. VLAN segments can have mode set to **bridge** or **irb**; transport VLANs must have the mode set to **route**. You can override the VLAN mode for individual devices to create scenarios like [router-on-a-stick](https://blog.ipspace.net/2022/10/netlab-router-stick/), but you can change the addressing behavior only with the VLAN **mode** parameter.

The only difference between **bridge** and **irb** mode is the assignment of IP addresses to the switch VLAN interface. When a switch operates in the **bridge** mode, its VLAN interface does not have an IP address. The VLAN **mode** does not impact the attached (non-VLAN-aware) devices.

## Addressing of VLAN Segments

*netlab* allocates an IP prefix from the **lan** pool to every VLAN segment[^VSD] in the global- or node **vlans** dictionary. For example, the following lab topology allocates an IP prefix to the **vx** VLAN and assigns the IP addresses from that prefix to H1, H2, and SW.

[^VSD]: VLAN with **mode** parameter set to **bridge** or **irb** (the default value).

```yaml
vlans:
  vx:
    links: [ h1-sw, h2-sw ]

nodes:
  h1:
  h2:
  sw:
    module: [ vlan ]
```

You can inspect the VLAN prefix with the **netlab inspect** command:

```text
$ netlab inspect vlans
vx:
  host_count: 3
  id: 1000
  neighbors:
  - ifname: eth1
    ipv4: 172.16.0.1/24
    node: h1
  - ifname: vlan1000
    ipv4: 172.16.0.3/24
    node: sw
  - ifname: eth1
    ipv4: 172.16.0.2/24
    node: h2
  prefix:
    allocation: id_based
    ipv4: 172.16.0.0/24
```

The **netlab report addressing** command can be used to display IP addresses assigned to the nodes attached to the VLAN segment (note that the physical links on SW are VLAN access links and thus have no IP addresses):

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **h1** |
| eth1 | 172.16.0.1/24 |  | h1 -> [sw,h2] |
| **h2** |
| eth1 | 172.16.0.2/24 |  | h2 -> [h1,sw] |
| **sw** |
| eth1 |  |  | [Access VLAN vx] sw -> h1 |
| eth2 |  |  | [Access VLAN vx] sw -> h2 |
| vlan1000 | 172.16.0.3/24 |  | VLAN vx (1000) -> [h1,h2] |

(tutorial-vlan-addressing-custom-segment)=
### Custom VLAN Segment Addressing

VLANs defined in the global **vlans** dictionary can have most of the [**links** attributes](link-attributes), including the **[prefix](addr-example-static)** and **[pool](addr-example-pool)** attributes. That makes it possible to assing VLAN prefixes from another pool or to use static VLAN prefixes.

For example, the following topology allocates a prefix to the **vx** VLAN from the **edge** pool:

```yaml
addressing.edge.ipv4: 10.42.0.0/16

vlans:
  vx:
    links: [ h1-sw, h2-sw ]
    pool: edge

nodes:
  h1:
  h2:
  sw:
    module: [ vlan ]
```

You can observe the effects of the changed IP prefix with the **netlab report addressing** command:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **h1** |
| eth1 | 10.42.0.1/24 |  | h1 -> [sw,h2] |
| **h2** |
| eth1 | 10.42.0.2/24 |  | h2 -> [h1,sw] |
| **sw** |
| eth1 |  |  | [Access VLAN vx] sw -> h1 |
| eth2 |  |  | [Access VLAN vx] sw -> h2 |
| vlan1000 | 10.42.0.3/24 |  | VLAN vx (1000) -> [h1,h2] |

Likewise, you can assign static IPv4 or IPv6 prefixes to a VLAN with the **prefix** attribute. The following topology assigns a static IPv6 prefix to the **vx** VLAN:

```yaml
vlans:
  vx:
    links: [ h1-sw, h2-sw ]
    prefix.ipv6: 2001:db8:0:42::/64

nodes:
  h1:
  h2:
  sw:
    module: [ vlan ]
```

These are the resulting addresses assigned to the three nodes attached to the VLAN:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **h1** |
| eth1 |  | 2001:db8:0:42::1/64 | h1 -> [sw,h2] |
| **h2** |
| eth1 |  | 2001:db8:0:42::2/64 | h2 -> [h1,sw] |
| **sw** |
| eth1 |  |  | [Access VLAN vx] sw -> h1 |
| eth2 |  |  | [Access VLAN vx] sw -> h2 |
| vlan1000 |  | 2001:db8:0:42::3/64 | VLAN vx (1000) -> [h1,h2] |

(tutorial-vlan-addressing-custom-node)=
### Custom Node Addressing on VLAN Segments

The end-nodes attached to a VLAN segment are treated as if they were attached to a regular link. You can use the **ipv4** and **ipv6** interface attributes to set the IP addresses of these interfaces. For example, the following topology sets the H1 IP address to 10.10.0.213 and the H2 IP address to 10.10.0.17.

```yaml
vlans:
  vx:
    prefix.ipv4: 10.10.0.0/24

nodes:
  h1:
  h2:
  sw:
    module: [ vlan ]

links:
- h1:
    ipv4: 10.10.0.213/24
  sw:
  vlan.access: vx
- h2:
    ipv4: 17
  sw:
  vlan.access: vx
```

Here's the corresponding addressing report:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **h1** |
| eth1 | 10.10.0.213/24 |  | h1 -> [sw,h2] |
| **h2** |
| eth1 | 10.10.0.17/24 |  | h2 -> [h1,sw] |
| **sw** |
| eth1 |  |  | [Access VLAN vx] sw -> h1 |
| eth2 |  |  | [Access VLAN vx] sw -> h2 |
| vlan1000 | 10.10.0.3/24 |  | VLAN vx (1000) -> [h1,h2] |

You cannot use the same trick with the VLAN-aware switches, as their physical interfaces (on VLAN access or trunk ports) do not have IP addresses; the VLAN-aware switches have VLAN addresses configured on the VLAN interfaces.

You must [use the node **vlans** dictionary](vlan-interface-parameters) to modify the parameters of the VLAN interfaces. For example, use the following topology to set the SW's IPv4 address of the VLAN (or IRB or SVI) interface associated with VLAN **vx**:

```yaml
vlans:
  vx:
    links: [ h1-sw, h2-sw ]
    prefix.ipv4: 10.10.0.0/24

nodes:
  h1:
  h2:
  sw:
    module: [ vlan ]
    vlans.vx.ipv4: 10.10.0.17/24
```

The corresponding addressing report generated with the `netlab report --node sw addressing.md` command reflects the change:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **sw** |
| eth1 |  |  | [Access VLAN vx] sw -> h1 |
| eth2 |  |  | [Access VLAN vx] sw -> h2 |
| vlan1000 | 10.10.0.17/24 |  | VLAN vx (1000) -> [h1,h2] |

## Transport VLAN Addressing

Transport VLANs are used to create multiple independent IP segments between adjacent nodes. A separate prefix from the **lan** or **p2p** pool[^BNCN] is thus allocated to every transport VLAN instance.

[^BNCN]: Based on the [number and roles of nodes attached to the link](links-default-pools).

For example, using the following topology, _netlab_ allocates two IP prefixes to the transport VLAN **tx**:

```yaml
defaults.device: frr
module: [ vlan ]

vlans:
  vx:
    mode: route
    links: [ s1-s2, s2-s3 ]

nodes: [ s1, s2, s3 ]
```

As you can see from the addressing report, _netlab_ allocates 10.1.0.0/30 to the S1-S2 link and 10.1.0.4/30 to the S2-S3 link:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **s1** |  10.0.0.1/32 |  | Loopback |
| eth1 | 10.1.0.1/30 |  | s1 -> s2 |
| **s2** |  10.0.0.2/32 |  | Loopback |
| eth1 | 10.1.0.2/30 |  | s2 -> s1 |
| eth2 | 10.1.0.5/30 |  | s2 -> s3 |
| **s3** |  10.0.0.3/32 |  | Loopback |
| eth1 | 10.1.0.6/30 |  | s3 -> s2 |

### Custom Transport VLAN Addressing

You can change the parameters of a transport VLAN within the global **vlans** dictionary, but cannot assign an IP prefix to a transport VLAN; _netlab_ would use that prefix on all VLAN instances, resulting in duplicate IP subnets. You can, however, change the prefix allocation parameters, like the addressing pool you want to use.

For example, the following topology assigns /31 prefixes to the point-to-point transport VLAN links:

```yaml
defaults.device: frr

addressing.core:
  ipv4: 10.42.0.0/24
  prefix: 31
  allocation: p2p

module: [ vlan ]

vlans:
  vx:
    links: [ s1-s2, s2-s3 ]
    mode: route
    pool: core

nodes: [ s1, s2, s3 ]
```

Here's the corresponding addressing report:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **s1** |  10.0.0.1/32 |  | Loopback |
| eth1 | 10.42.0.0/31 |  | s1 -> s2 |
| **s2** |  10.0.0.2/32 |  | Loopback |
| eth1 | 10.42.0.1/31 |  | s2 -> s1 |
| eth2 | 10.42.0.2/31 |  | s2 -> s3 |
| **s3** |  10.0.0.3/32 |  | Loopback |
| eth1 | 10.42.0.3/31 |  | s3 -> s2 |

### Custom Prefixes on Transport VLAN Links

Transport VLAN access links are identical to regular links as there's a single VLAN on the link, and the link uses no VLAN tagging. You can thus use the standard link attributes to change the parameters of a transport VLAN access link, for example:

```yaml
defaults.device: frr

module: [ vlan ]

vlans:
  vx:
    mode: route

nodes: [ s1, s2, s3 ]

links:
- interfaces: [ s1, s2 ]
  vlan.access: vx
  prefix.ipv4: 10.1.0.0/31
- interfaces: [ s2, s3 ]
  vlan.access: vx
  prefix.ipv4: 10.2.0.0/31
```

```{warning}
The above topology works only with transport VLANs. You cannot set any layer-3 parameters on VLAN access interfaces of VLAN segments; you have to set them within the node **vlans** dictionary (see [above](tutorial-vlan-addressing-custom-node))
```

These are the IP addresses assigned to the two links:

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **s1** |  10.0.0.1/32 |  | Loopback |
| eth1 | 10.1.0.0/31 |  | s1 -> s2 |
| **s2** |  10.0.0.2/32 |  | Loopback |
| eth1 | 10.1.0.1/31 |  | s2 -> s1 |
| eth2 | 10.2.0.0/31 |  | s2 -> s3 |
| **s3** |  10.0.0.3/32 |  | Loopback |
| eth1 | 10.2.0.1/31 |  | s3 -> s2 |

### Custom Interface Addressing on Transport VLAN Links

Transport VLAN links are not transformed into VLAN interfaces; _netlab_ uses native interfaces to implement VLAN access links and subinterfaces to implement VLAN trunks. As there's no VLAN interface involved, you can also set individual interface IP addresses on transport VLAN links, for example:

```yaml
module: [ vlan ]

vlans:
  vx:
    mode: route
  v2:
    mode: route

nodes: [ s1, s2 ]

links:
- vlan.access: vx
  s1:
    ipv4: 10.1.0.17/24
  s2:
    ipv4: 10.1.0.42/24
```

```{warning}
The above topology works only with transport VLANs. You cannot set any layer-3 parameters on VLAN access interfaces of VLAN segments; you have to set them within the node **vlans** dictionary (see [above](tutorial-vlan-addressing-custom-node))
```

Assigning custom interface IP addresses to transport VLANs in a VLAN trunk is a bit more cumbersome; you have to set the IP addresses within the interface **vlan.trunk** definition, for example:

```yaml
defaults.device: frr

module: [ vlan ]

vlans:
  v1:
    mode: route
  v2:
    mode: route

nodes: [ s1, s2 ]

links:
- s1:
    vlan.trunk:
      v1.ipv4: 10.1.0.17/24
      v2.ipv4: 10.2.0.17/24
  s2:
    vlan.trunk:
      v1.ipv4: 10.1.0.42/24
      v2.ipv4: 10.2.0.42/24
```

```{warning}
The above topology works only with transport VLANs. You cannot set any layer-3 parameters on VLAN trunk interfaces of VLAN segments; you have to set them within the node **vlans** dictionary (see [above](tutorial-vlan-addressing-custom-node))
```

This is the corresponding addressing report (note the use of VLAN subinterfaces like **eth1.1000**):

| Node/Interface | IPv4 Address | IPv6 Address | Description |
|----------------|-------------:|-------------:|-------------|
| **s1** |  10.0.0.1/32 |  | Loopback |
| eth1 |  |  | s1 -> s2 |
| eth1.1000 | 10.1.0.17/24 |  | s1 -> s2 |
| eth1.1001 | 10.2.0.17/24 |  | s1 -> s2 |
| **s2** |  10.0.0.2/32 |  | Loopback |
| eth1 |  |  | s2 -> s1 |
| eth1.1000 | 10.1.0.42/24 |  | s2 -> s1 |
| eth1.1001 | 10.2.0.42/24 |  | s2 -> s1 |
