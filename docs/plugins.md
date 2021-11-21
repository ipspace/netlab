# Custom Plugins

*netsim-tools* support dynamically loadable plugins allowing you to implement custom data model transformations without adding nerd knobs to the core topology transformation.

```{warning}
This is an experimental feature. There is no well-defined API; performing operations beyond simple data transformation might require digging through the source code. You might want to [open a discussion on *‌netsim-tools* GitHub repository](https://github.com/ipspace/netsim-tools/discussions) before proceeding.
```

Plugins needed by a topology file are listed in the **plugin** top-level element, for example:

```
plugin: [ bgp-anycast-no-ibgp ]

module: [ ospf, bgp ]

anycast.as: 65101
...
```

Plugins are Python files loaded from the current directory. They define well-known functions that are invoked during the topology transformation process which includes these steps:

* execute plugin **init** function
* check topology top-level elements
* adjust global parameters (defaults)
* adjust node list (turning dictionary into list if needed)
* adjust link list (turning shorthand notation into full-blown dictionary)
* setup address pools
* execute plugin **pre_transform** function
* execute module **pre_transform** function
* adjust groups (including setting node data from **node_data**)
* execute plugin **pre_node_transform** function
* transform node data
* execute plugin **post_node_transform** function
* execute plugin **pre_link_transform** function
* transform link data
* execute plugin **post_link_transform** function
* execute module **post_transform** function
* execute plugin **post_transform** function

Every plugin function is called with a single *topology* argument: the current topology data structure.

## Example

All anycast servers in a BGP anycast topology should have the same AS number, but do not need IBGP sessions between themselves. A custom plugin deletes IBGP sessions with an autonomous system defined in **anycast.as** topology attribute.

The topology file defines a plugin to load and sets (among other things) the **anycast.as** attribute. Please note that this attribute would not be recognized without the plugin:

```yaml
plugin: [ bgp-anycast-no-ibgp ]

module: [ ospf, bgp ]

anycast.as: 65101

defaults:
  device: iosv

bgp:
  as_list:
    65000:
      members: [ l1, l2, l3, s1 ]
      rr: [ s1 ]
    65101:
      members: [ a1,a2,a3 ]

nodes: 
  [ l1, l2, l3, s1, a1, a2, a3 ]

links: [ s1-l1, s1-l2, s1-l3, l2-a1, l2-a2, l3-a3 ]
```

The plugin imports **topology** augmentation module which defines the valid top-level elements. It also imports the **common** netsim module to create error messages.

```python
import sys
from box import Box
from netsim.augment import topology
from netsim import common
```

The **init** function adds **anycast** keyword to the list of valid top-level elements (figuring out what needs to be done might require wasting time looking at the source code):

```
def init(topo: Box) -> None:
  topology.topo_main_elements.append('anycast')
```

The custom transformation is executed as the last step of the topology transformation -- the **post_transform** function removes IBGP neighbors from all nodes in **anycast.as** autonomous system.

```
def post_transform(topo: Box) -> None:
  if not topo.anycast['as']:
    common.error('BGP anycast plugin needs an AS number')

  for node in topo.nodes:
    if 'bgp' in node:
      if node.bgp['as'] == topo.anycast['as']:
        node.bgp.neighbors = [ 
          n for n in node.bgp.neighbors 
            if n.type != 'ibgp' ]
```
