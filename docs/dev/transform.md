# Topology File Transformation

*netlab* performs a complex data transformation of the lab topology file to get device-level data that is then used to [create output files](../outputs/index.md) (Ansible inventory, Vagranfile...).

The data transformation has three major steps:

* [Setup](#setup-phase)
* [Global](#global-data-transformation), [node](#node-data-transformation) and [link](#link-data-transformation) data transformation
* [Final Steps and Cleanup](#final-steps-and-cleanup)

## Setup Phase

* Read topology file
* Read customer and system [default settings](../defaults.md) (`topology-defaults.yml`) and [merge them](../defaults.md#deep-merging) with the topology file (`netsim.read_topology.load`)
* Check for presence of required top-level topology elements (`netsim.augment.topology.check_required_elements`)
* Adjust the nodes data structure: transform [list of strings](nodes-list-of-strings) into a dictionary with empty values (`netsim.augment.nodes.create_node_dict`)
* Initialize node groups (`netsim.augment.groups.init_groups`):

	* Check the group data structures
	* Add group members based on nodes' **group** attribute
	* Check recursive groups
	* Copy group **device** and **module** attribute into nodes
	* Copy group **node_data** into nodes
	* Process **bgp.as_list** to get **bgp.as** node attributes
	* Create BGP autogroups (groups based on BGP AS numbers)
	* Copy **node_data** from BGP autogroups into nodes

* Adjust the list of links -- transform [strings or lists of nodes](../example/link-definition.md) into link dictionaries (`netsim.augment.links.adjust_link_list`)
* Initialize [plugin system](../plugins.md): load all plugins listed in the **plugin** top-level element (`netsim.augment.plugin.init`)
* Execute plugin **init** hook (`netsim.augment.plugin.execute`)
* Extend **default.attributes** with **default.extra_attributes** (`netsim.augment.topology.extend_attribute_list`)
* Adjust global parameters (`netsim.augment.topology.adjust_global_parameters`):

  * Set `provider` top-level element
  * Merge provider-specific device and addressing defaults with global defaults

* Load provider plugin (`netsim.providers._Provider.load`)
* Augment node provider data: set node device type, select VM/container image, copy provider-specific node data into node dictionary (`netsim.augment.nodes.augment_node_provider_data`)
* Augment node data with global defaults that are not part of configuration modules (example: MTU) (`augment.nodes.augment_node_system_data`)
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
* Set [link type](../links.md#link-types) based on the number of devices connected to the link (`netsim.augment.links.get_link_type`)
* [Augment link](../links.md#augmenting-link-data) and [node interface data](../links.md#augmenting-node-data) (`netsim.augment.links.augment_p2p_link` and `netsim.augment.links.augment_lan_link`):

  * If the link does not have a **prefix** attribute, get link prefix from the [corresponding address pool](../links.md#selecting-custom-address-pools)
  * Set node interface IP addresses to first and second subnet IP address for numbered P2P links.
  * Calculate node interface IP addresses from node ID and link prefix for all other links unless the on-link node data contains [static IP addresses](links.md#static-interface-addressing).
  * Copy link-level configuration module data into node interface data (example: OSPF area)
  * Create interface data for all nodes connected to the link ([details](../links.md#augmenting-node-data)).

* Execute **post_link_transform** plugin and module hooks

## Final Steps and Cleanup

* Execute **post_transform** module functions (`netsim.modules.post_transform`):

  * Check whether the lab devices support modules configured on them (`netsim.modules.check_supported_node_devices`)
  * Merge select node data into interface data (`netsim.modules.copy_node_data_into_interfaces`) -- this is how interfaces get default `ospf.area` from the node.
  * Execute **post_transform** [node-level module hook](#node-level-module-hooks)
  * Execute **post_transform** [link-level module hook](#link-level-module-hooks)
  * Sort node module lists in order of module dependencies -- a module dependent on another module will be configured after it (`netsim.modules.reorder_node_modules`)

* Execute **post_transform** plugin hooks
* Merge group-level and node-level [custom deployment templates](../groups.md#custom-configuration-templates) (`netsim.augment.groups.node_config_template`)
* Delete temporary data structures from the topology (list of plugin modules, addressing pools, pointer to provider module)

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
