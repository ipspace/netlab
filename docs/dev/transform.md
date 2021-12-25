# Topology File Transformation

The *netsim-tools* library performs a complex data transformation of the lab topology file to get device-level data that is then used to [create output files](../outputs/index.md) (Ansible inventory, Vagranfile...).

The data transformation has three major steps:

* [Setup](#setup-phase)
* [Global](#global-data-transformation), [node](#node-data-transformation) and [link](#link-data-transformation) data transformation
* [Final Steps and Cleanup](#final-steps-and-cleanup)

## Setup Phase

* Read topology file
* Read customer and system [default settings](../defaults.md) (`topology-defaults.yml`) and [merge them](../defaults.md#deep-merging) with the topology file (`netsim.read_topology.load`)
* Initialize [plugin system](../plugins.md): load all plugins listed in the **plugin** top-level element (`netsim.augment.plugin.init`)
* Execute plugin **init** hook (`netsim.augment.plugin.execute`)
* Extend **default.attributes** with **default.extra_attributes** (`netsim.augment.topology.extend_attribute_list`)
* Check for presence of required top-level topology elements (`netsim.augment.topology.check_required_elements`)
* Adjust global parameters (`netsim.augment.topology.adjust_global_parameters`):

  * Set `provider` top-level element
  * Merge provider-specific device and addressing defaults with global defaults

* Load provider plugin (`netsim.providers._Provider.load`)
* Adjust the list of nodes -- transform [list of strings](nodes.md#list-of-strings) or [dictionary of nodes](nodes.md#dictionary-of-nodes) into list of node objects (dictionaries) (`netsim.augment.nodes.adjust_node_list`)
* Augment node provider data: set node device type, select VM/container image, copy provider-specific node data into node dictionary (`netsim.augment.nodes.augment_node_provider_data`)
* Adjust the list of links -- transform [strings or lists of nodes](links.md#link-formats-example) into link dictionaries (`netsim.augment.links.adjust_link_list`)
* Setup [addressing pools](../addressing.md) (`netsim.addressing.setup`)

## Global Data Transformation

* Execute **pre_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Execute [**pre_transform** module adjustments](#adjust-global-module-parameters) (`netsim.modules.adjust_modules`)
* Execute **pre_transform** [node-](#node-level-module-hooks) and [link-level](#link-level-module-hooks) module hooks
* Adjust node groups (`netsim.augment.groups.adjust_groups`):

	* Validate group data structures
	* Use node-level **group** parameter to adjust group members
	* Copy group-level **node_data** settings into all member nodes

* Validate top-level topology elements[^VTE] (`netsim.augment.topology.check_global_elements`)

[^VTE]: Top-level elements have to be validated after the configuration modules have been initialized. See Issue#61 for details.

## Node Data Transformation

* Execute **pre_node_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Set unique ID for every node
* Get loopback IP addresses, management MAC address, and management IP addresses (`netsim.augment.nodes.augment_mgmt_if`) from *loopback* and *mgmt* address pools
* Execute **augment_node_data** provider hook (example: set **hostname** for *containerlab* nodes)
* Execute **post_node_transform** plugin hooks 

## Link Data Transformation

* Execute **pre_link_transform** plugin hooks (`netsim.augment.plugin.execute`)
* Check [link attributes](../links.md#link-attributes) (`netsim.augment.links.check_link_attributes`)
* Set [link type](../links.md#link-types) based on the number of devices connected to the link (`netsim.augment.links.get_link_type`)
* [Augment link](../links.md#augmenting-link-data) and [node interface data](../links.md#augmenting-node-data) (`netsim.augment.links.augment_p2p_link` and `netsim.augment.links.augment_lan_link`):

  * If the link does not have a **prefix** attribute, get link prefix from the [corresponding address pool](../links.md#selecting-custom-address-pools)
  * Set node interface IP addresses to first and second subnet IP address for numbered P2P links.
  * Calculate node interface IP addresses from node ID and link prefix for all other links unless the on-link node data contains [static IP addresses](links.md#static-interface-addressing).
  * Copy link-level configuration module data into node interface data (example: OSPF area)
  * Create interface data for all nodes connected to the link ([details](../links.md#augmenting-node-data)).

* Execute **post_link_transform** plugin hooks

## Final Steps and Cleanup

* Execute **post_transform** module functions (`netsim.modules.post_transform`):

  * Check whether the lab devices support modules configured on them (`netsim.modules.check_supported_node_devices`)
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
* Add global module settings (`adjust_global_modules`):

	* Add node-specific modules to global list of modules 
	* Merge module default settings with topology default settings 
	* Copy global module settings into topology settings, skipping global module attributes listed in module **no_propagate** attribute.

* Check global-, node- and link-level module parameters against the list of allowed module attributes (specified under module settings in system defaults) (`check_module_parameters`)
* Check module dependencies (for example: SR-MPLS module can only be used with IS-IS module) (`check_module_dependencies`)
* Execute module-level **module_pre_default** hook
* Execute **node_pre_default** hooks
* Execute **link_pre_default** hooks
* Deep merge global-level module settings with node-level settings.

### Node-Level Module Hooks

For every node using the specified module, execute **node_** hook (**node_pre_default**, **node_pre_transform**, **node_post_transform**).

### Link-Level Module Hooks

For every link that has at least one node using the specified module, execute **link_** hook (**link_pre_default**, **link_pre_transform**, **link_post_transform**).
