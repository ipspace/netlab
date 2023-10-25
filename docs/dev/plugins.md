# Developing Plugins

Plugins are either Python files or directories containing Python code plus configuration templates. They are loaded from the user search path[^USP] or `netsim/extra` _networklab_ package directory.

[^USP]: User search path includes current directory, `~/.netlab` and `/etc/netlab`.

For simple plugins, the plugin name specifies the file name (without the `.py` extension). For plugin packages, the plugin name specifies the directory with `plugin.py` Python module and optional plugin defaults (`defaults.yml`) and Jinja2 templates (one per supported **netlab_device_type**/**ansible_network_os**).

```{warning}
This is an underdocumented feature. Performing operations beyond simple data transformation might require digging through the source code. You might want to [open a discussion on *netsim-tools* GitHub repository](https://github.com/ipspace/netlab/discussions) before proceeding.
```

Plugins can define well-known functions that are invoked during the [topology transformation process](transform.md) which includes these steps:

* execute plugin **init** function
* check topology top-level elements
* adjust global parameters (defaults), node list, link list, and address pools
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

Every plugin function is called with a single *topology* argument: the current topology data structure. The node- or link-manipulation functions must iterate over `topology.nodes` dictionary or `topology.links` list.

Plugins extending [configuration modules](../modules.md) might have to define additional module attributes. The [module attribute lists](module-attributes.md) have to be extended with the plugin defaults or in the plugin **init** function before any module validation code is executed.

## Plugin Metadata

Plugin can specify global variables that are used to influence the plugin behavior or order-of-execution:

* `_requires`: A list of prerequisite modules and plugins. _netlab_ will abort if any of the prerequisite plugins is not listed in the **topology.plugin** list, or if any of the prerequisite modules is not used by at least one node.
* `_execute_after`: A list of plugins that should execute before the current plugin. For example, **ebgp.multihop** plugin has to execute after **ebgp.utils** plugin, and therefore defines `_execute_after = [ 'ebgp.utils' ]`
* `_config_name`: The name of extra configuration templates to add to the node **config** attribute when a node using the plugin functionality requires additional device configuration.  The value of this variable is set during the plugin initialization process, but it's still recommended to define it in the plugin and set its value to a string to prevent **mypy** complaints.

## Sample Plugin

All anycast servers in a BGP anycast topology should have the same AS number, but [do not need IBGP sessions between themselves](https://blog.ipspace.net/2022/01/netsim-plugins.html). A [custom plugin](https://github.com/ipspace/netlab-examples/tree/master/plugins/adjust-bgp-sessions) deletes IBGP sessions for any node with **bgp.anycast** attribute.

The topology file used in the BGP anycast example uses [group node data](../groups.md#setting-node-data-in-groups) on a [BGP AS group](../groups.md#automatic-bgp-groups) to set **bgp.anycast** node attribute on any node in AS 65101

```yaml
plugin: [ bgp.anycast ]

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
    bgp.anycast: 10.42.42.42/32

nodes:
  [ l1, l2, l3, s1, a1, a2, a3 ]

links: [ s1-l1, s1-l2, s1-l3, l2-a1, l2-a2, l3-a3 ]
```

The **bgp.anycast** attribute is defined in the plugin defaults (`anycast/defaults.yml`) (see [](validation.md) for details):

```
bgp.attributes.node.anycast:
  type: ipv4
  use: prefix
```

The plugin imports **netsim.api** module to get access to the plugin helper functions.

```python
import sys
from box import Box
from netsim import api
```

The custom transformation is executed as the last step of the topology transformation -- the **post_transform** function removes IBGP neighbors from all nodes with **bgp.anycast** attribute.

```
def post_transform(topo: Box) -> None:
...
  for node in topo.nodes.values():
    if 'bgp' in node:
      if 'anycast' in node.bgp:
        node.bgp.advertise_loopback = False
        node.bgp.neighbors = [
          n for n in node.bgp.neighbors
            if n.type != 'ibgp' ]
...
```

The **post_transform** function also sets the **config** node parameter to deploy [custom configuration template](custom-config) that creates additional loopback interface with the anycast IP address.

```
def post_transform(topo: Box) -> None:
  global _config_name
  for node in topo.nodes.values():
    if 'bgp' in node:
      if 'anycast' in node.bgp:
...
        api.node_config(node,_config_name)
```

Notes:

* The global `_config_name` variable is set during the plugin initialization process.
* `api.node_config` appends the specified custom configuration template to the list of node configuration templates. While equivalent to...\
  \
  `node.config.append(template)`\
  \
  ... the utility function handles edge cases like missing **config** attribute or duplicate configuration templates.

