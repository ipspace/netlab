# Nodes (Network Devices)

Network devices (nodes) used in a virtual lab are specified in **nodes** element in the topology file. Nodes can be specified as:

* A list of strings
* A dictionary of node names and node attributes
* A list of node objects

Regardless of the format used, the [topology transformation process](dev/transform.md) converts the **nodes** element into a dictionary of dictionaries before further processing.

## List of Strings

The easiest way to specify nodes in a virtual lab topology is to list node names as a list of strings:

```
---
defaults:
  device: iosv
  
nodes:
- r1
- r2
- r3
```

When using this format you cannot specify the device types or any other node attributes. Default device type specified in **defaults.device** is used for all nodes specified in this manner.

## Dictionary of Nodes

When you have to specify additional node attributes, or when you're building a lab topology containing multiple device types, specify nodes as a dictionary of node objects (dictionaries). 

You can specify the device type (if non-default) in **device** attribute, and add any additional attributes you need (for example, BGP AS number). Per-node attributes specified in a node dictionary are copied into Ansible inventory.

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

## List of Node Objects

You could also use a list of node objects. In this format, the node name is specified in the **name** attribute. You might want to use this format with older versions of Python 3 to ensure the nodes get consistent node IDs.

Simple example:

```
nodes:
- name: c_ios
  device: iosv
- name: c_csr
  device: csr
- name: c_nxos
  device: nxos
- name: a_eos
  device: eos
- name: j_vsrx
  device: vsrx
```

More complex example with additional node attributes:

```
nodes:
- name: e1
  module: [ ospf, bgp ]
  bgp:
    as: 65000
- name: e2
  module: [ ospf ]
  edge: true
- name: pe1
  device: csr
  module: [ ospf, bgp ]
  bgp:
    as: 65001
```

You can also combine the list formats, specifying some nodes as strings (using default device type) and others as objects:

```
nodes:
- e1
- e2
- name: pe1
  device: nxos
```

## Augmenting Node Data

After the initial cleanup, *netsim-tools* topology transformation code augments node data as follows (bold text indicates attribute names):

* Unless the node data contain an **id** attribute[^id], the node **id** is set based on node's position in the **nodes** dictionary[^IDLIST] -- starting with 1 and skipping static **id** used by other nodes.
* **loopback** addresses are fetched from *loopback* [address pool](addressing.md). IPv4 loopback addresses are commonly using node **id** as the last octet. IPv6 loopback addresses are commonly using node **id** as the last byte in the IPv6 prefix.
* **device** type is copied from **defaults.device** if not already set.
* Vagrant **box** is set from device data if not specified in the node attributes
* Management interface parameters are saved in **mgmt** element. Management interface name (**ifname**) is computed from device data. **mac** address and **ipv4** and **ipv6** addresses are computed from corresponding parameters in *mgmt* pool. You can overwrite any of these parameters (at your own risk) by specifying them in **mgmt** dictionary within node data.

[^id]: Node **id** must be an integer between 1 and 250. When using the standard management interface IP addressing (where management IPv4 addresses start with .100), the node **id** should not exceed 150.

[^IDLIST]: Python 3.7 and later retains the order of elements within a dictionary. Node IDs are thus assigned to devices in the order you used in YAML topology file. Node IDs might change sporadically if you use older Python versions; in that case, use  one of the list formats of the **nodes** element.

### Examples

The following **nodes as a list of strings** topology data...

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

The following **nodes as a dictionary** topology data...

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

The following topology data with one of the nodes having a static **id**...

```
defaults:
  device: cumulus

nodes:
  r1:
  r2:
  r3:
    id: 1
```

... results in the following node data:

```
nodes:
- box: CumulusCommunity/cumulus-vx
  device: cumulus
  id: 2
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: eth0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
  name: r1
- box: CumulusCommunity/cumulus-vx
  device: cumulus
  id: 3
  loopback:
    ipv4: 10.0.0.3/32
  mgmt:
    ifname: eth0
    ipv4: 192.168.121.103
    mac: 08-4F-A9-00-00-03
  name: r2
- box: CumulusCommunity/cumulus-vx
  device: cumulus
  id: 1
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: eth0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
  name: r3
```
