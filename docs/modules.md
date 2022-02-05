# Optional Configuration Modules

Network topology could refer to additional *configuration modules* that can be used to deploy routing protocols or network services in addition to initial device configuration.

Module-specific parameters can be added to:

* Nodes, links or interfaces[^INTF]
* Topology (global node settings)
* **defaults** element in the topology, topology defaults, or global defaults.
* Default **devices** settings[^BRAVE]

[^INTF]: Node data within a link dictionary
[^BRAVE]: For the brave souls only. Probably best left alone.

**Notes:**
* Global module parameters will be merged with node-specific parameters (see *[merging default values](#merging-default-values)* for details).
* Link-level module parameters will be merged with interface data.
* Select node-level parameters (example: OSPF area) are merged into interface data.
* Further processing of module-specific data is module-dependent.

## Specifying Configuration Modules

* The default configuration modules used in a network topology are specified in **module** top-level element, for example:

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
  module: [ ospf, bgp ]
- name: c_csr
  device: csr
- name: j_vsrx
  device: vsrx
  module: []
```

... OSPF and BGP will be configured on **c_nxos**, OSPF will be configured on **c_csr** and no extra configuration will be performed on **j_vsrx**.

## Module-Specific Node and Link Attributes

Module names can be used as elements in **links** and **nodes** structures to set module-specific link- or node attributes. You also set module attributes on individual interfaces (node data within a link object)

You can also use module names to set global parameters (top-level topology elements).

**Notes:**

* The list of [allowed link attributes](links.md#link-attributes) is automatically extended with global module names.
* Global parameters are merged with per-node data. See *[merging default values](#merging-default-values)* for details.

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

The link between R1, R2 and R3 should also be in area 0. The OSPF cost on R1 should be set to 10:

```
- r1:
    ospf.cost: 10
  r2:
  r3:
  ospf:
    area: 0
    cost: 3
```

## Using Modules when Deploying Device Configurations

During the initial device configuration, the **[netlab initial](../netlab/initial.md)** command generates and deploys configuration snippets for every module specified on individual network devices.

**Notes:**

* The configuration snippets are created from templates in the **netsim/ansible/templates/_module_** directory.
* The device-specific template is selected based on **ansible_network_os** value. For example, `netsim/ansible/templates/ospf/eos.j2` will be used to create OSPF configuration for an Arista EOS device.

For more information, see [list of configuration modules](module-reference.md)

## Merging Default Values

Module parameters are dictionaries of values stored under the *module-name* key in defaults, topology, node, link, or interface. The only exception to this rule: you can disable a few protocols (example: [BFD](module/bfd.md)) on an interface, with **_module_: False** configuration setting.

Node module parameters are adjusted based on topology parameters and defaults ([more details](dev/module-attributes.md)):

* Global and topology defaults are merged with the **defaults** setting in topology file (see [*topology defaults*](defaults.md) and *[merging defaults](addressing.md#merging-defaults)*)
* For every module used in network topology, the default module parameters are merged with topology-level settings.
* For every node, the topology-level settings for modules used by that node are merged with the node-level settings.
* Final node-level settings are saved into expanded topology file or Ansible inventory, and used by configuration templates.

Link module parameters are not changed during the topology expansion. They are merged with interface data when individual interfaces are created during the topology transformation process, and later augmented with module-specific subset of node data (example: OSPF area).

### Example

The module parameter defaults will be illustrated with the following OSPF+BGP topology. The topology uses **defaults** element for simplicity reasons; you could specify the same parameters in topology- or global defaults.

```
defaults:
  device: iosv
  ospf:
    area: 0.0.0.0
    process: 2
  bgp:
    as: 65000

module: [ ospf ]
ospf:
  process: 1

nodes:
  r1:
    ospf:
      router_id: 10.0.0.17
      area: 0.0.0.1
  r2:
    module: [ bgp,bfd ]
```

Before the merge process starts, the global list of modules is augmented with node-specific modules, resulting in:

```
module: [ ospf,bgp,bfd ]
```

For every module used in network topology, the default values are added to global parameter values, resulting in:

```
ospf:
  area: 0.0.0.0
  process: 1
bgp:
  as: 65000
```

**Notes:**
* OSPF area is taken from defaults;
* OSPF process ID is specified as a global parameter and is not overwritten with a default value;
* Even though there was no global BGP setting, it's copied from the defaults.

Finally, the global settings are merged with node settings, resulting in:

```
nodes:
  r1:
    ospf:
      area: 0.0.0.1
      router_id: 10.0.0.17
      process: 1
  r2:
    bgp:
      as: 65000
```

**Notes:**
* OSPF area was specified for R1, and is not replaced.
* OSPF process ID was not specified for R1. It's copied from the global OSPF parameters.
* OSPF router ID was specified for R1, but not in global parameters. It's not changed.
* R2 had no BGP parameters. BGP parameters were copied from global BGP parameters.
