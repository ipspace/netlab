# Build a Leaf-and-Spine Fabric

The *fabric* plugin builds a leaf-and-spine topology and adds the generated groups, nodes, and links to the lab topology.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using the Plugin

* Add `plugin: [ fabric ]` to lab topology.
* Configure fabric parameters with the **fabric** attribute.

The plugin is invoked early in the _netlab_ topology transformation process and adds fabric groups, nodes, and links to the lab topology. Set **fabric.debug** to `True` to view the generated data structures.

## Configuring Fabric Parameters

The plugin is configured with the **fabric** topology-level dictionary that has these parameters:

| Parameter  | Type    | Meaning |
|------------|---------|---------|
| **spines** | integer | Number of spine devices |
| **leafs**  | integer | Number of leaf devices  |
| **spine**  | dictionary | Spine parameters |
| **leaf**   | dictionary | Leaf parameters |
| **debug**  | boolean | Print generated topology elements |

You can specify these leaf- and spine parameters in the **leaf** and **spine** dictionaries:

| Parameter | Type | Meaning |
|-----------|------|---------|
| **name**  | format string | node name template |
| **group** | string | _netlab_ group that contains the leaf- or spine devices |

These parameters have the following defaults:

| Parameter | Spine default | Leaf default |
|-----------|---------------|--------------|
| **name**  | `S{count}`    | `L{count}`   |
| **group** | `spines`      | `leafs`      |

All other leaf- and spine parameters are copied into the corresponding _netlab_ groups or evaluated and copied into fabric nodes if they are format strings (strings containing `{`).

## Examples

(fabric-ospf)=
### Create a Simple Fabric Running OSPF

The following lab topology creates a leaf-and-spine fabric with four leaves (L1 through L4) and two spines (S1 and S2). All nodes are Arista EOS switches running OSPF.

```yaml
defaults.device: eos
module: [ ospf ]
plugin: [ fabric ]
fabric.spines: 2
fabric.leafs: 4
```

(fabric-host)=
### Connect Hosts to the Fabric

The **fabric** plugin adds nodes and links to the lab topology, which can also contain other nodes and links. As you know the names of the generated nodes, you can connect them to other devices.

The following lab topology has two hosts connected to L1 and L4. L1 and L4 are created by the **fabric** plugin.

```yaml
defaults.device: eos
module: [ ospf ]
plugin: [ fabric ]
fabric.spines: 2
fabric.leafs: 4

nodes:
  H1:
    device: linux
  H2:
    device: linux
    
links:
- H1-L1
- H2-L2
```

```{tip}
To ensure consistent interface naming on the fabric nodes, the **fabric** plugin *prepends* its links to the **links** list. H1  will be connected to L1's third Ethernet interface (the first two interfaces connect L1 to S1 and S2).
```

### Building an IBGP + IGP fabric

Building an IBGP fabric with route reflectors running on spine switches requires just minor modifications to [](fabric-ospf) scenario:

* Add **bgp** module to the list of modules
* Set global **bgp.as** parameter to the BGP AS number
* Set **bgp.rr** parameter in the **spines** group to *True*

```yaml
defaults.device: eos
module: [ ospf,bgp ]
plugin: [ fabric ]
fabric.spines: 2
fabric.leafs: 4

groups:
  spines:
    bgp.rr: True
```

### Building an EBGP fabric

Building an EBGP fabric in which every leaf switch has a different AS number is slightly more complex. As in the previous example, we can use the **spines** group to define the spine-layer ASN number, but we'll use another approach to be consistent with the leaf setup. We'll use an additional **fabric.leaf** parameter that sets per-leaf BGP ASN:

```yaml
defaults.device: eos
module: [ ospf,bgp ]
plugin: [ fabric ]
fabric:
  spines: 2
  leafs: 4
  spine.bgp.as: 65100
  leaf.bgp.as: '{65000 + count}'
```
