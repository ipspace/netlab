# Lab Topology Attribute Validation

_netlab_ includes a comprehensive validation framework that checks attributes of all core topology elements and optional configuration modules. Valid attributes, their data types and other constraints are defined in `attributes` dictionary within `topology-defaults.yml` file and within individual module definitions.

Various data model transformation routines check:

* Global attributes defined in `attributes.global`
* Address pool attributes defined in `attributes.pool`
* Group attributes defined in `attributes.group` and augmented with `attributes.node`
* Node attributes defined in `attributes.node`
* Link attributes combined from `attributes.link` and `attributes.link_internal`
* Interface attributes combined from `attributes.interface` and `attributes.link` but without `attributes.link_no_propagate`
* VLAN attributes defined in `attributes.vlan`
* VRF attributes defined in `attributes.vrf`
* Prefix attributes defined in `attributes.prefix`

Group, node, link, interface, VLAN and VRF attributes are augmented with module attributes based on modules configured on individual groups, nodes (node and interface attributes) or the list of all modules used in a lab topology (link, VLAN, VRF attributes).

**attributes** dictionary has additional elements that define extra attributes and propagation of attributes between lab topology objects:

* **internal** global attributes are valid but not checked
* **link_internal** link attributes are valid but not checked
* Link module attributes are copied to interface attributes unless the module is mentioned in **link_module_no_propagate** list
* Pool attributes are copied to prefixes unless they are mentioned in the **pool_no_copy** list
* Node attributes mentioned in the **node_copy** list are copied into node's interfaces
* Global module attributes are copied into node attributes unless they're listed in a module **no_propagate** list
* Individual modules could use additional values in **attributes** dictionary. For example, the VLAN module uses **vlan_no_propagate** list to control which VLAN attributes are not copied into links or SVI interfaces.

Attribute types that are validated (**global**, **node**, **link**, **interface**, **pool**, **prefix**, **vlan**, **vrf**) can be specified as a list (in which case only the attribute names are validated) or as a dictionary (in which case the data types of individual attributes can be validated).

For example, IS-IS module requires just the attribute name validation -- the global, node, and link[^IFN] attribute names are specified as lists:

[^IFN]: Link attributes are also valid interface attributes.

```
isis:
  attributes:
    global: [ af, area, type, bfd ]
    node: [ af, area, net, type, bfd ]
    link: [ metric, cost, type, bfd, network_type, passive ]
```

EIGRP module wants to have its attribute checked, so it's using a dictionary of attributes together with their data types:

```
eigrp:
  supported_on: [ csr, iosv, nxos, none ]
  transform_after: [ vlan,vrf ]
  config_after: [ vlan ]
  as: 1
  attributes:
    global:
      af:
        ipv4: bool
        ipv6: bool
      as: { type: int, min_value: 1, max_value: 65535 }
    node:
      af:
        ipv4: bool
        ipv6: bool
      as: { type: int, min_value: 1, max_value: 65535 }
    link:
      passive: bool
```

As you can see, the dictionary-based approach allows in-depth validation of nested attributes.

Using the dictionary-based approach, each attribute could be:

* Another dictionary without the **type** key (use for nested attributes)
* A string specifying the desired data type (**str**, **int**, **bool**, **list** or **dict**)
* A dictionary specifying the validation parameters.

Every dictionary specifying the validation parameters must have a **type** attribute (data type as a string) and might include additional parameters as follows:

All data types:
* **true_value** -- value to use when the parameter is set to *True*

**str**, **list** or **dict**:
* **valid_values** -- list of valid values (keys for dictionary)

**list** or **dict**:
* **create_empty** -- _True_ if you want to create an empty element if it's missing

**int**: 
* **min_value** -- minimum parameter value
* **max_value** -- maximum parameter value
