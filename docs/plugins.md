# Custom Plugins

*netsim-tools* support dynamically loadable plugins allowing you to implement custom data model transformations without adding nerd knobs to the core topology transformation.

```{warning}
This is an experimental feature. There is no well-defined API; performing operations beyond simple data transformation might require digging through the source code. You might want to [open a discussion on *‌netsim-tools* GitHub repository](https://github.com/ipspace/netsim-tools/discussions) before proceeding.
```

Plugins needed by a topology file are listed in the **plugin** top-level element, for example:

```
plugin: [ bgp-anycast-no-ibgp ]

module: [ ospf, bgp ]
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

All anycast servers in a BGP anycast topology should have the same AS number, but do not need IBGP sessions between themselves. A custom plugin deletes IBGP sessions for any node with **bgp.anycast** attribute.

This is the topology file used in BGP anycast example. It uses [**node_data** attribute](groups.md#setting-node-data-in-groups) on a [BGP AS group](groups.md#automatic-bgp-groups) to set **bgp.anycast** node attribute on any node in AS 65101

```yaml
plugin: [ bgp-anycast-no-ibgp ]

module: [ ospf, bgp ]

defaults:
  device: iosv

bgp:
  as_list:
    65000:
      members: [ l1, l2, l3, s1 ]
      rr: [ s1 ]
    65101:
      members: [ a1,a2,a3 ]

groups:
  as65101:
    node_data:
      bgp.anycast: 10.42.42.42/32

nodes: 
  [ l1, l2, l3, s1, a1, a2, a3 ]

links: [ s1-l1, s1-l2, s1-l3, l2-a1, l2-a2, l3-a3 ]
```

The plugin imports **common** netsim module to create error messages.

```python
import sys
from box import Box
from netsim import common
```

The custom transformation is executed as the last step of the topology transformation -- the **post_transform** function removes IBGP neighbors from all nodes with **bgp.anycast** attribute.

```
def post_transform(topo: Box) -> None:
  for node in topo.nodes:
    if 'bgp' in node:
      if 'anycast' in node.bgp:
        node.bgp.advertise_loopback = False
        node.bgp.neighbors = [
          n for n in node.bgp.neighbors
            if n.type != 'ibgp' ]
```
