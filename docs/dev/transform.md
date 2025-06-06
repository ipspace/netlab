# Topology File Transformation

*netlab* performs a complex data transformation of the lab topology file to get device-level data that is then used to [create output files](../outputs/index.md) (Ansible inventory, Vagranfile...).

The data transformation has three major steps:

* [Setup](#setup-phase)
* [Global](#global-data-transformation), [node](#node-data-transformation) and [link](#link-data-transformation) data transformation
* [Final Steps and Cleanup](#final-steps-and-cleanup)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Setup Phase

* Read topology file
* Read customer and system [default settings](../defaults.md) (`topology-defaults.yml`) and [merge them](../defaults.md#deep-merging) with the topology file (`netsim.read_topology.load`)
* Perform the basic sanity checks (`netsim.augment.topology.topology_sanity_check`)
* Check minimum _netlab_ version (`netsim.utils.versioning.check_topology_version`)
* Adjust the nodes data structure: transform [list of strings](nodes-list-of-strings) into a dictionary with empty values (`netsim.augment.nodes.create_node_dict`)
* Check basic group data structures and auto-create nodes from group members (`augment.groups.precheck_groups`)
* Initialize [plugin system](../plugins.md): load all plugins listed in the **plugin** top-level element (`netsim.augment.plugin.init`)
* Initialize [node roles](node-router-host) subsystem
* Execute plugin **topology_expand** hook (`netsim.augment.plugin.execute`) for plugins that augment lab topology structures (example: [](../plugins/fabric.md))

* Initialize the link list (`netsim.augment.links.links_init`)
  * Transform [strings or lists of nodes](../example/link-definition.md) into link dictionaries (`netsim.augment.links.adjust_link_list`)
  * Set link names (`netsim.augment.links.set_linknames`)
  * Expand [link groups](link-groups) (`netsim.augment.links.expand_groups`)
  * Set **linkindex** attributes (`netsim.augment.links.set_linkindex`)

* Expand topology components (`netsim.augment.components.expand_components`)
* Initialize **groups** structure and perform basic sanity checks (`netsim.augment.groups.init_groups`)

	* Check the mandatory attributes in the group data structures
	* Add group members based on nodes' **group** attribute
	* Check recursive groups

* Execute plugin **init** hook (`netsim.augment.plugin.execute`)
* Check for the presence of required top-level topology elements (`netsim.augment.topology.check_required_elements`)

* Initialize attribute validation (`netsim.data.validate.init_validation`)
* Execute data normalization static module hook (`netsim.modules.execute_module_hooks`):
* Adjust global parameters (`netsim.augment.topology.adjust_global_parameters`):

  * Set `provider` top-level element
  * Merge provider-specific device and addressing defaults with global defaults

* Validate group parameters (`netsim.augment.groups.validate_groups`)
* Copy group data into nodes (`netsim. augment.groups.copy_group_data`)

	* Copy group **device** and **module** attribute into nodes
	* Copy group **node_data** into nodes
	* Process **bgp.as_list** to get **bgp.as** node attributes
	* Create BGP autogroups (groups based on BGP AS numbers)
	* Copy **node_data** from BGP autogroups into nodes

* Select primary provider and load provider plugin(s) (`netsim.providers.select_primary_provider`)
* Augment node provider data: set node device type, select VM/container image, copy provider-specific node data into node dictionary (`netsim.augment.nodes.augment_node_provider_data`)
* Augment node data with global defaults that are not part of configuration modules (example: MTU) (`augment.nodes.augment_node_system_data`)
* Process external **tools** (`augment.tools.process_tools`)
* Setup [addressing pools](../addressing.md) (`netsim.addressing.setup`)

## Global Data Transformation

* Execute **pre_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Execute [**pre_transform** module adjustments](#adjust-global-module-parameters) (`netsim.modules.adjust_modules`)
* Execute **pre_transform** [node-](#node-level-module-hooks) and [link-level](#link-level-module-hooks) module hooks
* Validate top-level topology elements (`netsim.augment.topology.check_global_elements`)

## Node Data Transformation

* Execute **pre_node_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Execute **pre_node_transform** module hooks (`netsim.modules.pre_node_transform`)
* Set unique ID for every node
* Get loopback IP addresses, management MAC address, and management IP addresses (`netsim.augment.nodes.augment_mgmt_if`) from *loopback* and *mgmt* address pools
* Execute **augment_node_data** provider hook (example: set **hostname** for *containerlab* nodes)
* Execute **post_node_transform** plugin and module hooks

## Link Data Transformation

* Execute **pre_link_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Execute **pre_link_transform** module hooks (`netsim.modules.pre_link_transform`)
* Check [link attributes](../links.md#link-attributes) (`netsim.augment.links.check_link_attributes`)
* Set [link type](links-types) based on the number of devices connected to the link (`netsim.augment.links.get_link_type`)
* [Augment link](../links.md#augmenting-link-data) and [node interface data](../links.md#augmenting-node-data) (`netsim.augment.links.augment_p2p_link` and `netsim.augment.links.augment_lan_link`):

  * If the link does not have a **prefix** attribute, get link prefix from the [corresponding address pool](links-custom-pools)
  * Set node interface IP addresses to first and second subnet IP address for numbered P2P links.
  * Calculate node interface IP addresses from node ID and link prefix for all other links unless the on-link node data contains [static IP addresses](../links.md#static-interface-addressing).
  * Copy link-level configuration module data into node interface data (example: OSPF area)
  * Create interface data for all nodes connected to the link ([details](../links.md#augmenting-node-data)).

* Execute **post_link_transform** plugin and module hooks

## Final Steps and Cleanup

* Transform the lab validation data structure (`netsim.augment.validate.process_validation`)
* Execute **post_transform** module functions (`netsim.modules.post_transform`):

  * Check whether the lab devices support modules configured on them (`netsim.modules.check_supported_node_devices`)
  * Merge select node data into interface data (`netsim.modules.copy_node_data_into_interfaces`) -- this is how interfaces get default `ospf.area` from the node.
  * Execute **post_transform** [node-level module hook](#node-level-module-hooks)
  * Execute **post_transform** [link-level module hook](#link-level-module-hooks)
  * Sort node module lists in order of module dependencies -- a module dependent on another module will be configured after it (`netsim.modules.reorder_node_modules`)

* Execute **post_transform** plugin hooks
* Merge group-level and node-level [custom deployment templates](custom-config) (`netsim.augment.groups.node_config_template`)
* Cleanup node data in `augment.nodes.cleanup` function (prune the `_daemon_config` dictionary, check for duplicate ifname/ifindex)
* Execute **post_transform** primary provider hook and node-specific **node_post_transform** provider hooks.
* Process device quirks
* Cleanup links: remove empty **links** list and **_linkname** attribute from individual links
* Cleanup groups: remove settings (keys starting with '\_') from **groups** dictionary
* Execute **cleanup** module hooks
* Execute **cleanup** plugin hooks
* Delete temporary data structures from the topology: list of plugin modules, addressing pools, and pointers to provider modules.

## Configuration Module Transformations

`netsim.modules` module contains these transformations

### Adjust Global Module Parameters

* Add global modules to all nodes that do not have a **module** parameter (`augment_node_modules`)
* Adjust global module settings: add node-specific modules to global list of modules (`adjust_global_modules`)
* Execute module-level **init** hook
* Adjust node module parameters (`merge_node_module_params`):

  * Add global module parameters to node data
  * Add device-specific module parameters to node data
  * Add system default settings to node data

  **Note:** In all cases, skip module attributes listed in module **no_propagate** attribute.

* Adjust global module parameters (`merge_global_module_params`)

	* Copy system default module settings into topology settings, skipping module attributes listed in module **no_propagate** attribute.
	* Reorder the global list of modules based on **transform_after** module attribute

  **Note:** global module parameters have to be adjusted after node parameters to get the desired node/global/device/default precedence.
  
* Enable additional module parameters specified in the lab topology
* Check global-, node- and link-level module parameters against the list of allowed module attributes (specified under module settings in system defaults) (`check_module_parameters`)
* Check module dependencies (for example: SR-MPLS module can only be used with IS-IS module) (`check_module_dependencies`)
* Execute module-level **module_pre_default** hook
* Execute **node_pre_default** hooks
* Execute **link_pre_default** hooks

### Node-Level Module Hooks

For every node using the specified module, execute **node_** hook (**node_pre_default**, **node_pre_transform**, **node_post_transform**).

### Link-Level Module Hooks

For every link that has at least one node using the specified module, execute **link_** hook (**link_pre_default**, **link_pre_transform**, **link_post_transform**).

(dev-transform-debugging)=
## Debugging the Transformation Process

`netlab create` command (the primary user of the transformation process) has a hidden `--debug` option that sets numerous debugging flags, allowing you to debug a subset of transformation components.

The following debugging flags can be used in _netlab_ release 1.6.4[^DF] to debug the core components:

* **all**: turn on all debugging flags
* **addr**: debug addressing pools
* **addressing**: debug IPAM logic
* **cli**: debug CLI actions
* **defaults**: debug user/system defaults
* **groups**: debug netlab group processing
* **links**: debug the core link transformation code
* **modules**: debug generic configuration module routines
* **plugin**: debug plugin loading process and plugin calls
* **template**: debug common Jinja2 templating routines
* **validate**: debug the data validation logic

Some modules are so complex that we gave them separate debugging flags:

* **vlan**: debug VLAN module
* **vrf**: debug VRF module

You can also debug components involved in lab management process:

* **external**: debug invocation of external programs
* **libvirt**: debug _libvirt_ provider
* **status**: debug the 'lab status' code
* **quirks**: debug device quirks code

[^DF]: Execute `netlab create --debug help` to display the up-to-date set of debugging flags. The error message will tell you `help` value is an invalid choice for the `--debug` argument but also display the valid values.