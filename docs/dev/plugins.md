(dev-plugins)=
# Developing Plugins

Plugins are either Python files or directories containing Python code plus configuration templates. *netlab* tries to locate them in the *plugin search path* (specified in the **defaults.paths.plugin** setting), which usually includes the user search path and the `netsim/extra` _networklab_ package directory.

```{tip}
You can inspect the plugin search path with the **netlab show defaults paths.plugin** command and [modify it if needed](change-search-paths).
```

The plugin name specifies either a Python file name (without the `.py` extension) or a directory with the `plugin.py` Python module, optional plugin defaults (`defaults.yml`), and Jinja2 templates (one per supported **netlab_device_type**/**ansible_network_os**).

```{warning}
This is an underdocumented feature. Performing operations beyond simple data transformation might require digging through the source code. Before proceeding, you might want to [open a discussion on *netlab* GitHub repository](https://github.com/ipspace/netlab/discussions).
```

(dev-plugin-hooks)=
## Plugin Hooks

Plugins can define well-known functions that are invoked during the [topology transformation process](transform.md), which includes these steps:

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

Every plugin function is called with a single *topology* argument: the current topology data structure. The node or link-manipulation functions must iterate over the `topology.nodes` dictionary or the `topology.links` list.

Plugins extending [configuration modules](../modules.md) might have to define additional module attributes. The [module attribute lists](module-attributes.md) must be extended before any module validation code is executed, either with the plugin defaults or in the plugin **init** function.

(dev-plugin-cli-hooks)=
## Plugin CLI Hooks

Plugins are usually used in the data transformation process, but could also be used in later stages of configuration file creation and lab management.

A plugin can add its name to the `defaults.netlab.create.plugin` list to be called at the time the configuration files are created:

* The `output` hook is called before any output modules are called and before netlab finalizes the [search path lists](change-search-paths).
* The `post_output` hook is called after the output modules have created the configuration files.

A plugin can also be called during the **[netlab up](netlab-up)**/**[netlab down](netlab-down)** processing:

* The plugin must add its name to the `defaults.netlab._command_.plugin` list (where _command_ is **up** or **down**)
* Whenever a netlab command calls a [CLI hook](dev-cli-hooks), it calls the plugin pre-shell hook before the CLI command is executed and the plugin post-shell hook after the CLI command has successfully completed[^SC]
* The plugin hook name is created from the CLI hook name and the `pre_shell_` and `post_shell_` prefixes. For example, `pre_shell_pre_start_lab` hook is called before the `pre_start_lab` CLI command is executed, and the `post_shell_pre_start_lab` hook is called after the CLI command has completed.

[^SC]: The post-shell hook is obviously not called if the CLI command fails.

## Plugin Metadata

A plugin can specify global variables that are used to influence the plugin's behavior or order of execution:

* `_requires`: A list of prerequisite modules and plugins. _netlab_ will abort if any prerequisite plugins are not listed in the **topology.plugin** list, or if any of the prerequisite modules are not used by at least one node.
* `_execute_after`: A list of plugins that should execute before the current plugin. For example, the **ebgp.multihop** plugin has to be executed after **ebgp.utils** plugin, and therefore defines `_execute_after = [ 'ebgp.utils' ]`
* `_config_name`: The name of extra configuration templates to add to the node **config** attribute when a node using the plugin functionality requires additional device configuration. This variable is set during the plugin initialization process, but it's still recommended to define it in the plugin and set its value to a string to prevent **mypy** complaints.

## Plugin Defaults

A directory containing the `plugin.py` Python module can include plugin defaults (`defaults.yml`). The contents of the `defaults.yml` file are merged with the topology defaults after processing **merge** and **copy** requests for attributes and device features.

### Merging Attributes

Within the `defaults.yml` file, you can copy an attribute definition from another attribute with the **copy** or **merge** parameter that contains the namespace of the other attribute. The **copy**/**merge** parameter must be specified on a top-level attribute within an attribute namespace.

For example, the **bgp.session** plugin copies the node definition of the **bgp.gtsm** attribute from the global definition. This is the relevant part of the `defaults.yml` file:

```
bgp:
  attributes:
    global:
      gtsm:
        type: int
        min_value: 1
        max_value: 254
        true_value: 1

    node:
      gtsm:
        copy: global
```

### Merging Device Features

If your plugin relies on device **features**, you can copy/merge them between similar devices with the **copy** or **merge** keyword anywhere below the device name. For example, this is the definition of BGP policy features for all IOS-based devices:

```
devices:
  iosv.features.bgp:
    _default_locpref: True
    bandwidth:
      in: auto
  cat8000v:
    copy: iosv
  csr:
    copy: iosv
  iol:
    copy: iosv
  ioll2:
    copy: iosv
```

## Sample Plugin

All anycast servers in a BGP anycast topology should have the same AS number but [do not need IBGP sessions between themselves](https://blog.ipspace.net/2022/01/netsim-plugins.html). A [custom plugin](https://github.com/ipspace/netlab-examples/tree/master/plugins/adjust-bgp-sessions) deletes IBGP sessions for any node with **bgp.anycast** attribute.

The topology file used in the BGP anycast example uses [group node data](groups-object-data) on a [BGP AS group](groups-bgp) to set **bgp.anycast** node attribute on any node in AS 65101

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

The **post_transform** function also sets the **config** node parameter to deploy a [custom configuration template](custom-config) that creates additional loopback interface with the anycast IP address.

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

* The global `_config_name` variable is set during the plugin initialization.
* `api.node_config` appends the specified custom configuration template to the list of node configuration templates. While equivalent to...\
  \
  `node.config.append(template)`\
  \
  ... the utility function handles edge cases like a missing **config** attribute or duplicate configuration templates.

