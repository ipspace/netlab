# Nodes (Network Devices)

Network devices (nodes) used in a virtual lab are specified in **nodes** element in the topology file. Nodes can be specified as:

* A list of strings
* A dictionary of node names and node attributes
* A list of node objects

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

## List of Node Objects

When you have to specify additional node attributes, or when you're building a lab topology containing multiple device types, specify nodes as a list of node objects (dictionaries). Node name is specified in **name** attribute, device type (if non-default) in **device** attribute. 

You can add any additional attributes you need (for example, BGP AS number). Additional per-node attributes specified in a node dictionary are copied into Ansible inventory.

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

You can also combine the first two formats, specifying some nodes as strings (using default device type) and others as objects:

```
nodes:
- e1
- e2
- name: pe1
  device: nxos
```

## Dictionary of Nodes

You can also specify the nodes as a dictionary of node objects, for example:

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

Nodes specified as a dictionary are converted into a list sorted by node names before further processing.

## Augmenting Node Data

After the initial cleanup, *netsim-tools* topology transformation code augments node data as follows (bold text indicates attribute names):

* Node **id** is set based on node's position in the list starting with 1
* **loopback** addresses are fetched from *loopback* [address pool](addressing.md). IPv4 loopback addresses are commonly using node **id** as the last octet. IPv6 loopback addresses are commonly using node **id** as the last byte in the IPv6 prefix.
* **device** type is copied from **defaults.device** if not already set.
* Vagrant **box** is set from device data if not specified in the node attributes
* Management interface parameters are saved in **mgmt** element. Management interface name (**ifname**) is computed from device data. **mac** address and **ipv4** and **ipv6** addresses are computed from corresponding parameters in *mgmt* pool. You can overwrite any of these parameters (at your own risk) by specifying them in **mgmt** dictionary within node data.

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
