# Nodes (Network Devices)

Network devices (nodes) used in a virtual lab are specified in the **nodes** element in the topology file. 

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Specifying Nodes in Lab Topology

Nodes (lab devices) can be specified as:

* A list of strings (node names)
* A dictionary of node names and node attributes

(nodes-list-of-strings)=
### Nodes Specified as a List of Strings 

The easiest way to specify nodes in a virtual lab topology is to list node names as a list of strings:

```
---
defaults:
  device: iosv
  
nodes: [ r1, r2, r3 ]
```

You cannot specify the device types or any other node attributes when using this format. The default device type specified in **defaults.device** is used for all nodes defined in this manner.

The [topology transformation process](dev/transform.md) converts the **nodes** element specified as a list of strings into a dictionary of dictionaries before further processing.

```{tip}
Node names can have up to 16 characters. To increase the maximum node name length, set the `defaults.const.MAX_NODE_ID_LENGTH` attribute (see also: [changing defaults](topo-defaults)).
```

### Dictionary of Nodes

When you have to specify additional node attributes or when you're building a lab topology containing multiple device types, specify nodes as a dictionary of node objects (dictionaries). 

You can specify the device type (if non-default) in the **device** attribute and add any additional attributes you need (for example, BGP AS number). Per-node attributes specified in a node dictionary are copied into the Ansible inventory.

In the following example, E1 and PE1 run OSPF and BGP in AS 65000, and PE1 uses a non-default device type (`csr`). There are no additional attributes specified for E2.

```
nodes:
  e1:
    module: [ ospf, bgp ]
    bgp:
      as: 65000
  e2:
  pe1:
    device: csr
    module: [ ospf, bgp ]
    bgp:
      as: 65000
```

(node-attributes)=
## Node Attributes

*netlab* uses the following node attributes (in alphabetical order):

* **config** -- extra [configuration templates](custom-config) applied to this device.
* **cpu** -- virtual CPU cores allocated to the VM lab device. It does not apply to container-based devices.
* **device** -- device type (see [supported platforms](platforms.md)). [Default device type](default-device-type) is specified in **defaults.device**.
* **group** -- list of [groups](topo-groups) this node belongs to.
* **id** -- static node identifier[^id] (see below)
* **image** or **box** -- specifies the Vagrant box or Docker container used by the lab device. Default images for individual device types are defined in system defaults and can be changed with **defaults.devices...** settings ([more details](default-device-image)).
* **loopback** -- [non-standard loopback addresses](node-loopback).
* **memory** -- memory allocated to the VM lab device. It does not apply to container-based devices.
* **module** -- the list of [configuration modules](modules.md) used by this node.
* **mgmt** -- management IPv4/IPv6 addresses. Used primarily with the [**external** provider](labs/external.md)
* **mtu** -- sets device-wide (*system*) MTU. This MTU is applied to all interfaces that don't have an explicit MTU ([more details](links-mtu)).
* **provider** -- virtualization provider used by this node (see [](labs/multi-provider.md) for more details).
* **role** -- when set to **host**, the device does not get a loopback IP address and [uses static routing](node-router-host) toward the [default gateway](links-gateway) ([more details](node-router-host))
* **unmanaged** -- when set to *True*, the node is not managed or configured by *netlab*. Use this parameter when integrating *netlab* topologies with additional external devices, which should not be configured by *netlab* ([more details](external-unmanaged)).

```{tip}
* The [Supported Virtualization Providers](platforms.md#supported-virtualization-providers) section of [Supported Platforms](platforms.md) lists the default **memory** and **cpu** values for all devices that can be run as virtual machines.
* You still have to specify the device type (either in the node or as the [default device type](default-device-type)) for unmanaged nodes. _netlab_ uses the device type to determine which features a node supports. If you want to use an unsupported unmanaged device, set **‌device** to **‌none**.
```

(node-loopback)=
## Loopbacks

You can use the **loopback** node attribute to change the [default allocation of loopback addresses](addressing-loopback). 

The **loopback** attribute could be set to:

* *True* -- add a loopback to the device even though the device wouldn't have it otherwise (for example, add loopbacks to Linux hosts)
* *False* -- do not create a loopback interface on this device (for example, do not create a loopback interface on a router)
* A dictionary containing loopback prefixes (**ipv4** and/or **ipv6** attributes) or an alternate addressing pool (**pool** attribute[^LBIN]).

The **ipv4** and **ipv6** attributes in the **loopback** dictionary can be set to a CIDR prefix (static loopback address) or a boolean value:

* *True* -- allocate a prefix from this address family from the specified addressing pool (useful to override group defaults on individual nodes)
* *False* -- do not allocate a prefix from this address family to the loopback interface

[^LBIN]: The alternate pool you use for IPv4 loopback addresses should have **loopback** in its name (to tell _netlab_ to set the allocated prefix length to /32) or a [**prefix** attribute](address-pool-specs), preferably set to 32. The IPv6 prefix length is automatically set to /64 unless you specify it with the **prefix6** attribute.

(node-ansible-data)=
## Overriding Ansible Variables

In node data, you can also override Ansible group variables starting with `ansible_` or `netlab_`. For example, to use SSH instead of Docker to connect to a Linux container, set `ansible_connection` to `ssh` in the node data:

```
nodes:
  ssh_host:
    device: linux
    provider: clab
    ansible_connection: ssh
```

(nodes-provider-attributes)=
## Provider-Specific Node Attributes

Some node attributes are used only with a specific *netlab* virtualization provider. These attributes can be specified at the node level as `<provider>.<attribute>` or as a default with `defaults.devices.<device>.<provider>.node.<attribute>`.

(nodes-provider-attributes-libvirt)=
### Libvirt Attributes

* **libvirt.nic_model** -- *libvirt* virtual NIC model used by the VM lab device. See *libvirt* and *KVM* documentation for supported values; the most common settings are *virtio* (*libvirt* default) and *e1000*. Other supported values include *rtl8139*, *pcnet*, *ne2k_pci*, *i82559er*, *i82557b*, *i82551* and *ne2k_isa*.

Example:
```
---
defaults.devices.vyos.libvirt.node.nic_model: e1000

nodes:
  vyos1:
    device: vyos
  vyos2:
    device: vyos
    libvirt.nic_model: virtio
```

```{tip}
The [Supported Virtualization Providers](platforms.md#supported-virtualization-providers) section of [Supported Platforms](platforms.md) lists the default **nic_model** for all devices that can be run as virtual machines.
```

(nodes-provider-attributes-clab)=
### Containerlab Attributes

When using network devices with *containerlab*, you might have to set these node attributes:

* **clab.type** -- device *type* when supported by containerlab (example: [SR Linux](https://containerlab.dev/manual/kinds/srl/#types))
* **clab.license** -- license file needed for a network device running under containerlab. Used by Nokia SR OS.

You will probably have to set other *containerlab* attributes to run networking-related tools or daemons as Docker containers within your lab. Please read the [*containerlab* provider documentation](labs/clab.md) for more details.

Example: set node type and license file for Nokia SR OS
```yaml
---
defaults.devices.sros.clab:
  image: vrnetlab/vr-sros:23.3.R3
  mtu: 1500
  node:
    type: ixr-ec
    license: ../../sros/license-sros23.3.R3.txt

nodes:
  e1:
    mtu: 1400
    clab:
      type: sr-1
```

(node-augment)=
## Augmenting Node Data

After the initial cleanup, the *netlab* [topology transformation code](dev/transform.md) augments node data as follows (bold text indicates attribute names):

* Unless the node data contain an **id** attribute, the node **id** is set based on node's position in the **nodes** dictionary[^IDLIST] -- starting with 1 and skipping static **id** used by other nodes.
* Unless the node is a *host*[^HOST], or has a **loopback** attribute, it's loopback addresses are fetched from *loopback* [address pool](addressing.md). IPv4 loopback addresses commonly use node **id** as the last octet. IPv6 loopback addresses commonly use node **id** as the last byte in the IPv6 prefix.
* **device** type is copied from **defaults.device** if not already set.
* Vagrant **box** (or Docker container name) is set from device data if not specified in the **box** or **image** node attributes
* Device settings **role** and **mtu** are copied into the node data unless you set the corresponding node attribute in the topology file.
* Management interface parameters are saved in the **mgmt** element. Management interface name (**ifname**) is computed from device data. **mac** address and **ipv4** and **ipv6** addresses are computed from corresponding parameters in *mgmt* pool. You can overwrite any of these parameters (at your own risk) by specifying them in the **mgmt** dictionary within node data.
* Device interfaces created as needed during the link transformation phase and collected in the **interfaces** list.
* [](modules.md) document describes further processing done on configuration module parameters.

[^id]: Node **id** must be an integer between 1 and 250. When using the standard management interface IP addressing (where management IPv4 addresses start with .100), the node **id** should not exceed 150.

[^HOST]: Identified by **role: host** attribute

[^IDLIST]: Python versions supported by _netlab_ retain the order of elements within a dictionary. Node IDs are thus assigned to devices in the order you used in the YAML topology file. Node IDs might change sporadically if you use older Python versions; in that case, use one of the list formats of the **nodes** element.

### Examples

The following list of nodes...

```
defaults:
  device: iosv

nodes:
- e1
- e2
- e3
```

... results in the following node data:

```
nodes:
- device: iosv
  id: 1
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
  name: e1
- device: iosv
  id: 2
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
  name: e2
- device: iosv
  id: 3
  loopback:
    ipv4: 10.0.0.3/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.103
    mac: 08-4F-A9-00-00-03
  name: e3
```

The following dictionary of nodes...

```
defaults:
  device: iosv

nodes:
  e1:
    igp: [ ospf ]
    edge: true
  e2:
  pe1:
    device: csr
    igp: [ ospf ]
```

... results in the following node data:

```
nodes:
- device: iosv
  edge: true
  id: 1
  igp:
  - ospf
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
  name: e1
- device: iosv
  id: 2
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: GigabitEthernet0/0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
  name: e2
- device: csr
  id: 3
  igp:
  - ospf
  loopback:
    ipv4: 10.0.0.3/32
  mgmt:
    ifname: GigabitEthernet1
    ipv4: 192.168.121.103
    mac: 08-4F-A9-00-00-03
  name: pe1
```

The following topology data, including a node with a static **id**:

```
defaults:
  device: frr

nodes:
  r1:
  r2:
  r3:
    id: 1
```

... results in the following ID assignments:

```
$ netlab create
$ netlab inspect --node all id
┏━━━━┳━━━━┳━━━━┓
┃ r1 ┃ r2 ┃ r3 ┃
┡━━━━╇━━━━╇━━━━┩
│ 2  │ 3  │ 1  │
└────┴────┴────┘
```

## Advanced Topics

```eval_rst
.. toctree::
   :maxdepth: 1

   node-roles.md
```
