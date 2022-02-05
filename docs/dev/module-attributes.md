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

The list of valid module attributes is specified in the **defaults._module_.attributes** dictionary:

* **global** -- valid global (topology-level) attributes
* **node** -- valid node-level attributes
* **link** -- valid link attributes
* **link_no_propagate** -- link module attributes that should not be propagated into interface data
* **interface** -- valid interface attributes

You can [extend the list of valid module attributes](../extend-attributes.md) with **defaults._module_.extra_attributes** dictionary.

## Propagating Module Attributes

Node-level module attributes are calculated during the [pre-transform module processing](transform.md#adjust-global-module-parameters):

* Default global attributes are [deep-merged](../defaults.md#deep-merging) with topology global attributes.
* Global attributes are deep-merged with node attributes (apart from *no_propagate* exceptions).
* Device-specific global attributes are deep-merged with node attributes.

The deep merge process takes care of attribute specificity:

* Attributes specified on individual nodes are not overwritten with global- or device-specific settings.
* Global attributes are not overwritten with device-specific attributes.
* This process is applied recursively across nested dictionaries as long as the node value of a specific attribute is a dictionary.

## Propagating Link Attributes

Node interfaces (**links** list within a node dictionary) are created from the topology **links** definition ([details](../links.md)). During that process, the link-level attributes are deep-merged with interface attributes specified on individual nodes within a link dictionary (apart from *no_propagate* exceptions).

Some modules support node attributes that can be used as a default value for interface attributes (example: OSPF area). The merging of node- and interface attributes have to be performed in the device configuration template, for example:

```
interface {{ l.ifname }}
 ip ospf {{ pid }} area {{ l.ospf.area|default(ospf.area) }}
```

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
