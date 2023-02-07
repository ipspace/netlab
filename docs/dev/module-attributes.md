# Configuration Module Attributes

The _[Module-Specific Node and Link Attributes](../modules.md#module-specific-node-and-link-attributes)_ and _[Merging Default Values](../modules.md#merging-default-values)_ parts of _Optional Configuration Modules_ document describe module attributes from an end-user perspective. This document adds the internal information needed by a developer aiming to:

* Extend an existing module with [custom attributes](../extend-attributes.md) or [plugins](../plugins.md)
* Create a new configuration module. 

## Specifying Module Attributes

Configuration modules could have:

* Default global attributes specified in **defaults** section, for example **defaults.bgp.as**
* Device-specific global attributes specified in **defaults.devices** section, for example **defaults.devices.srlinux.sr.srgb**
* Global attributes specified in topology file, for example **bgp.as**
* Node attributes specified on individual nodes.
* Link attributes specified on individual links, for example **ospf.area**
* Interface attributes specified within node data on individual link, for example **r1.ospf.cost**.

## Valid Module Attributes

Valid module attributes are specified in a sub-dictionary of the the **defaults._module_.attributes** dictionary:

* **global** -- valid global (topology-level) attributes
* **node** -- valid node-level attributes
* **link** -- valid link attributes
* **link_no_propagate** -- link module attributes that should not be propagated into interface data
* **node_copy** -- node module attributes that should be copied into interface attributes
* **interface** -- valid interface attributes

Module attributes for an individual module are stored (together with other module-specific data) in `netsim/modules/<modname>.yml` file.

You can [extend the list of valid module attributes](../extend-attributes.md) by adding new keys to the corresponding dictionary within **defaults._module_.attributes**. See [](validation.md) for more details.

## Propagating Module Attributes

Node-level module attributes are calculated during the [pre-transform module processing](transform.md#adjust-global-module-parameters). Default module attributes are [deep-merged](../defaults.md#deep-merging) with node attributes (apart from *no_propagate* exceptions) in the following order:

* Global module attributes from in the lab topology
* Device-specific module attributes specified in **defaults.devices._device_._module_** setting
* Default module attributes specified in **defaults._module_** setting

The deep merge process takes care of attribute specificity:

* Attributes specified on individual nodes are not overwritten with global- or device-specific settings.
* Topology-level attributes are not overwritten with device-specific attributes.
* Device-specific attributes are not overwritten with global system defaults.

## Propagating Link Attributes

Node interfaces (**interfaces** list within a node dictionary) are created from the topology **links** definition ([details](../links.md)). During that process, the link-level attributes are deep-merged with interface attributes specified on individual nodes within a link dictionary (apart from *no_propagate* exceptions).

Some modules support node attributes that can be used as a default value for interface attributes (example: OSPF area). These modules should list those attributes in **defaults._module_.attributes.node_copy** list to have them merged with the interface attributes that can then be easily used in configuration templates.

**Example**: OSPF area can be specified for a whole node or for an interface. 

Without the **node_copy** processing, the configuration templates would have to check for interface-level and node-level OSPF area:

```
interface {{ l.ifname }}
 ip ospf {{ pid }} area {{ l.ospf.area|default(ospf.area) }}
```

However, as **defaults.ospf.attributes.node_copy** is set to `[ area ]`, the node **ospf.area** setting is automatically copied into interface data unless the **ospf.area** was configured on an interface or its parent link. The configuration template can now be simplified into:

```
interface {{ l.ifname }}
 ip ospf {{ pid }} area {{ l.ospf.area }}
```

**Note**: The system defaults set **ospf.area** to **0.0.0.0**. That value is copied to individual nodes that have no OSPF area specified, and further down into individual interfaces, making sure that `l.ospf.area` always has a usable value.

## no_propagate Attributes

Some global attributes are used solely to compute node- or interface attributes in the module-specific Python code, for example **bgp.ebgp_role** or **bgp.as_list**. It makes no sense to propagate these attributes to node data. To stop the propagation of a global attribute, add it to **_module_.no_propagate** list, for example:

```
bgp:
  no_propagate: [ ebgp_role, advertise_roles, rr_list, as_list ]
```

Likewise, some link attributes should not be propagated to interface data. For example, the **prefix** link attribute is irrelevant in interface data, as it's used to calculate interface IP addresses (the prefix length is copied into IP addresses anyway). 

The link attribute propagation is currently controlled with global **defaults.attributes.link_no_propagate** list. Extending that list with a module name would stop propagation of all module-specific attributes into interface data. If you need a more granular solution, remove extraneous interface attributes in **node_post_transform** module hook.

## To Propagate or Not to Propagate

Use this simple rule to decide whether you need to propagate global module attributes into node data:

* If you need an attribute to generate device configuration, it MUST be propagated into node data. Device configurations are usually generated with Ansible playbooks, and the global parameters are not copied into Ansible inventory.
* You don't need to propagate global attributes that modify the behavior of module-specific Python code, or are used to set node attributes within that code (copious examples in `netsim.modules.bgp`). 
