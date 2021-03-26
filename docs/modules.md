# Optional Configuration Modules

Network topology could refer to additional *configuration modules* that can be used to deploy routing protocols or network services in addition to initial device configuration. 

Module-specific data can be added to node- or link objects and will be propagated to the final node- and interface data structures. No further processing is performed on module-specific data when expanding network topology.

## Specifying Configuration Modules

* The configuration modules used in a network topology are specified in **module** top-level element, for example:

```
module: [ ospf ]
```

* The global list of configuration modules is inherited by all nodes in the network topology. You could change per-node list of configuration modules with the node-specific **module** element.

### Example

Given the following topology...

```
module: [ ospf ]
nodes:
- name: c_nxos
  device: nxos
  module: [ ospf, evpn ] 
- name: c_csr
  device: csr
- name: j_vsrx
  device: vsrx
  module: []
```

... OSPF and EVPN will be configured on **c_nxos**, OSPF will be configured on **c_csr** and no extra configuration will be performed on **j_vsrx**.

## Module-Specific Node and Link Attributes

Module names can be used as elements in **links** and **nodes** structures to set module-specific link- or node attributes. You can also use them to set global parameters (top-level topology elements).

**Notes:** 

* The list of [allowed link attributes](links.md#link-attributes) is automatically extended with global module names.
* Global parameters are *not* copied into per-node data. When using Ansible inventory, you'll get global parameter values as host variables because they're part of the **all** inventory group.

### Examples

All devices should use OSPF area 1: set it globally.

```
module: [ospf]
ospf:
 area: 1
 
nodes:
- r1
- r2
- r3
```

The default area for **R3** (used on all its interfaces unless specified otherwise) should be backbone area. Set a different OSPF area with a node attribute:

```
module: [ospf]
ospf:
 area: 1
 
nodes:
- r1
- r2
- r3:
    ospf:
      area: 0
```

The link between R2 and R3 should be in area 0. Set OSPF area with a link attribute. Also set OSPF cost to 3:

```
- r2:
  r3:
  ospf:
    area: 0
    cost: 3
```

## Using Modules when Deploying Device Configurations

During the initial device configuration, the **[initial-config.ansible](configs.md)** playbook generates and deploys configuration snippets for every module specified on individual network devices.

**Notes:**

* The configuration snippets are created from templates in the **templates/_module_** directory. 
* The device-specific template is selected based on **ansible_network_os** value. For example, `templates/ospf/eos.j2` will be used to create OSPF configuration for an Arista EOS device.

For more information, see [list of configuration modules](module-reference.md)
