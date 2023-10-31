# Lab Topology Attribute Validation

_netlab_ includes a comprehensive validation framework that checks attributes of all core topology elements and optional configuration modules. Valid attributes, their data types and other constraints are defined in `attributes` dictionary within `topology-defaults.yml` file and within individual module definitions.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Attribute Validation Basics

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

## Specifying Valid Attributes

Core- or module-specific attribute types that are validated (**global**, **node**, **link**, **interface**, **pool**, **prefix**, **vlan**, **vrf**) can be specified as a list (in which case only the attribute names are validated) or as a dictionary (in which case the data types of individual attributes can be validated).

This is how you could validate attribute names supported by IS-IS configuration module[^IFN]:

[^IFN]: Link attributes are also valid interface attributes.

```
isis:
  attributes:
    global: [ af, area, type, bfd ]
    node: [ af, area, net, type, bfd ]
    link: [ metric, cost, type, bfd, network_type, passive ]
```

More thorough attribute check is implemented for most configuration modules. For example, this is the definition of valid **gateway** attributes and their data types:

```
gateway:
  attributes:
    global:
      id: int
      protocol: { type: str, valid_values: [ anycast, vrrp ] }
      anycast:
        unicast: bool
        mac: mac
      vrrp:
        group: int
        priority: int
        preempt: bool
    node:
      protocol:
      anycast:
      vrrp:
    link:
      id: int
      ipv4: { type: ipv4, use: interface }
      protocol: { type: str, valid_values: [ anycast, vrrp ] }
      anycast:
        unicast: bool
        mac: mac
      vrrp:
        group: int
        priority: int
        preempt: bool
```

As you can see, the dictionary-based approach allows in-depth validation of nested attributes.

Using the dictionary-based approach, each attribute could be:

* Another dictionary without the **type** key (use for nested attributes)
* A string specifying the desired data type.
* A dictionary specifying the data type in **type** key and additional parameters (see [](dev-valid-data-types))

(dev-valid-data-types)=
## Valid Data Types

Validator recognizes standard Python data types (**str**, **int**, **bool**, **list** or **dict**) and networking-specific data types (**asn**, **ipv4**, **ipv6**, **rd**, **mac** and **net**).
 
Data type can be specified as a string (without additional parameters), or as a dictionary with a **type** attribute (data type as a string) and additional type-specific validation parameters.

For example, VLAN link parameters include **access** and **native** that can be any string value as well as **mode** that must have one of the predefined values:

```
vlan:
  attributes:
    link:
      access: str
      native: str
      mode:  { type: str, valid_values: [ bridge, irb, route] }
```

All data types support:
* **true_value** -- value to use when the parameter is set to *True*
* **_requires** -- a list of modules that must be enabled in global- or node context to allow the use of this attribute. See `vrfs` in `modules/vrf.yml` and `vlans` in `modules/vlan.yml` for more details.

**Examples**

The global **vlans** dictionary can be used only with the **vlan** module:

```
attributes:
  global:
    vlans:                        # vlans is a valid global parameter
      type: dict                  # It's a dictionary
      _requires: [ vlan ]         # ... that requires VLAN module
```

You can specify a list of BGP session types for the MPLS 6PE functionality. However, you can also specify a *True* value for the global **mpls.6pe** attribute to enable the feature. The *True* value gets translated into a default list (enable 6PE on IBGP sessions):

```
mpls:
  attributes:
    global:
      6pe: { type: list, true_value: [ ibgp ] }
```

### Further Data Type Validation options

**str**, **list** or **dict** support:
* **valid_values** -- list of valid values (keys for dictionary)

**list** or **dict** support:
* **create_empty** -- _True_ if you want to create an empty element if it's missing

**dict** supports:
* **_keys** -- valid dictionary keys. _netlab_ performs recursive validation of dictionary keys. Usually not used as you can use [shortcut definition](validation-shortcut-type)

**int** values can be range-checked: 
* **min_value** -- minimum parameter value
* **max_value** -- maximum parameter value

(validation-shortcut-type)=
## Shortcut Data Type Definitions

_netlab_ supports several shortcuts that make type definitions easier to create and read:

* A data type definition that is a string is transformed into a dictionary with **type** key.
* A data type definition that is a list will match a list value. The value of the data type definition is used as the list of valid values.
* A data type definition that is a dictionary without the **type** key will match a dictionary. Keys starting with '_' (data validation parameters) will be retained in the data type definition, all other keys will be transferred into `_keys` dictionary.

**String example**

```
device_name: str
```

is transformed into:

```
device_name:
  type: str
```

**List example:**

```
x: [ a,b,c ]
```

... is transformed into

```
x:
  type: list
  valid_values: [ a,b,c ]
```

**Dictionary example:**

```
af:
  _alt_types: [ NoneType ]
  ipv4: bool
  ipv6: bool
```

... is transformed into:

```
af:
  _alt_types: [ NoneType ]
  _keys:
    ipv4: bool
    ipv6: bool
```

(validate-user-types)=
## User-Defined Data Types

If you use the same data structure in multiple places, consider using user-defined data types. You can define them in **defaults.attributes** and use them to validate any attribute.

```{note}
When using user-defined data types, you have to specify them as a string value of a validated attribute. You cannot use user-defined data types as a value for **‌type** validation attribute.
```

For example, the **bgp.session** plugin defines BGP timers as `exbs_timers` user-defined data type:

```
attributes:                   # User-defined data types
  exbs_timers:                # BGP timers: keepalive, hold, min_hold -- integers with a value range
    keepalive:
      type: int
      min_value: 1
      max_value: 300
    hold:
      type: int
      min_value: 3
      max_value: 3600
    min_hold:
      type: int
      min_value: 3
      max_value: 3600
```

The `exbs_timers` data type is then used to validate **bgp.timers** global- and node attribute:

```
bgp:
  attributes:
    global:
      timers: exbs_timers
...
    node:
      timers: exbs_timers
```

Please note that the following definition (using `exbs_timers` as the value of `timers` **type** attribute) would not work:

```
bgp:
  attributes:
    global:
      timers:
        type: exbs_timers ### INVALID, WON'T WORK
```

You can use `_namespace` attribute within the user-defined data types to add attributes from other objects. For example, as you can use link attributes in VLAN definitions, the **vlan** definition (see `modules/vlan.yml`) includes the `_namespace` attribute:

```
attributes:
  vlan:                           # Define the VLAN object type
    id: { type: int, min_value: 1, max_value: 4095 }
    vni: { type: int, min_value: 1, max_value: 16777215 }
    mode: { type: str, valid_values: [ bridge, irb, route ] }
    prefix:
    _namespace: [ link ]          # VLANs can include link attributes
```

## Alternate Data Types

Some _netlab_ attributes could take a dictionary value, alternate values meaning _use default_ or _do whatever you want_, or a list of keys.

### Specifying Alternate Data Types

**_alt_types** list within a dictionary of valid attributes specifies alternate data types that can be used instead of a dictionary.

For example, **_igp_.af** attribute can take a dictionary of address families, or it could be left empty (_None_) to tell _netlab_ to use the address families defined on the node:

```
ospf:
  attributes:
    global:
      af:
        _alt_types: [ NoneType ]
        ipv4: bool
        ipv6: bool
```

### Dictionary Specified As a List

Some _netlab_ attributes that are supposed to be a dictionary can take a list value that is transformed into a dictionary: list elements become dictionary keys, and a default value is used for the dictionary values. To validate such attributes, add **_list_to_dict** key to the attribute specification. The **_list_to_dict** key specifies the default value used when converting a list into a dictionary

**_list_to_dict** parameter is commonly used with address family parameters. For example, OSPF allows **ospf.af** parameter to be a list of enabled address families or a dictionary of address families with true/false value, for example:

```
nodes:
- name: c_nxos
  device: nxos
  ospf.af: [ ipv4 ]
- name: c_csr
  device: csr
  ospf.af.ipv4: True
```

The attribute definition for **ospf.af** attribute uses **_list_to_dict** to cope with both:

```
ospf:
  attributes:
    global:
      af:
        _list_to_dict: True
        _alt_types: [ NoneType ]
        ipv4: bool
        ipv6: bool
```

## IP Address Validation

**ipv4** and **ipv6** validators have a mandatory **use** parameter that can take the following values:

* **interface** -- an IP address specified on an interface. Can take True/False value and does not have to include a prefix length.
* **prefix** -- an IP prefix. Can take True/False value and must include prefix length/subnet mask.
* **id** (IPv4 only) -- an IPv4 address or an integer. Use **id** for parameters like OSPF areas, BGP cluster IDs, or router IDs.

