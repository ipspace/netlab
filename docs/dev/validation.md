(dev-attribute-validation)=
# Lab Topology Attribute Validation

_netlab_ includes a comprehensive validation framework that checks attributes of all core topology elements and optional configuration modules. Valid attributes, their data types, and other constraints are defined in the `attributes` dictionary within the `topology-defaults.yml` file and individual module definitions.

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

Group, node, link, interface, VLAN, and VRF attributes are augmented with module attributes based on modules configured on individual groups, nodes (node and interface attributes), or the list of all modules used in a lab topology (link, VLAN, VRF attributes).

**attributes** dictionary has additional elements that define extra attributes and propagation of attributes between lab topology objects:

* **internal** global attributes are valid but not checked
* **link_internal** link attributes are valid but not checked
* Link module attributes are copied to interface attributes unless the module is mentioned in the **link_module_no_propagate** list
* Pool attributes are copied to prefixes unless they are mentioned in the **pool_no_copy** list
* Node attributes mentioned in the **node_copy** list are copied into node's interfaces
* Global module attributes are copied into node attributes unless they're listed in a module **no_propagate** list
* Individual modules could use additional values in the **attributes** dictionary. For example, the VLAN module uses the **vlan_no_propagate** list to control which VLAN attributes are not copied into links or SVI interfaces.

## Specifying Valid Attributes

Core- or module-specific attribute types that are validated (**global**, **node**, **link**, **interface**, **pool**, **prefix**, **groups**, **vlan**, **vrf**) are specified as dictionaries of valid attributes.

The keys of the data type definition dictionaries are the valid attribute names, the values are the attribute data type descriptions (see also [](dev-valid-special-keys)).

For example, this is the definition of valid **gateway** attributes and their data types:

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

The dictionary-based approach allows in-depth validation of nested attributes, where each attribute could be:

* Another dictionary without the **type** key (use for nested attributes)
* A string specifying the desired data type.
* A dictionary specifying the data type in **type** key, and containing additional parameters described in [](dev-valid-data-types).

(dev-valid-data-types)=
## Valid Data Types

Validator recognizes standard Python data types (**str**, **int**, **float**, **bool**, **list** or **dict**) and the following networking-specific data types:

| Data type.     | Meaning |
|----------------|---------|
| **addr_pool**  | [Address pool](address-pools) |
| **asn**        | AS number (2-octer or 4-octet) |
| **asn2**       | 2-octet ASN |
| **bool_false** | The only valid value is *false* |
| **device**     | Valid device (platform) identifier |
| **id**         | Identifier (containing A-Z, a-z, 0-9 and underscore) |
| **ipv4**       | An IPv4 address, prefix, integer (offset in a subnet), or bool (unnumbered) |
| **ipv6**       | An IPv6 address, prefix, integer (offset in a subnet), or bool (LLA only) |
| **mac**        | MAC address in any format recognized by the `netaddr` library |
| **named_pfx**  | [named prefix](named-prefixes) |
| **net**        | IS-IS NET/NSAP |
| **node_id**    | Valid node name |
| **prefix_str** | An IPv4 or IPv6 prefix |
| **rd**         | Route distinguisher (ASN:ID or IP:ID) |
| **r_proto**    | Routing protocol identifier |
| **time**       | Time duration specified in seconds (`s`) or milliseconds (`ms`) |
 
The data type can be specified as a string (without additional parameters) or a dictionary with a **type** attribute (data type as a string) and other type-specific validation parameters.

For example, VLAN link parameters include **access** and **native**, which can be any string value, as well as **mode** that must have one of the predefined values:

```
vlan:
  attributes:
    link:
      access: str
      native: str
      mode:  { type: str, valid_values: [ bridge, irb, route] }
```

All attributes defined with a dictionary (**mode** in the above example, but not **access** or **native**) can use the following validation parameters:

* **true_value** -- value to use when the parameter is set to *True*
* **_requires** -- a list of modules that must be enabled in global- or node context to allow the use of this attribute. See `vrfs` in `modules/vrf.yml` and `vlans` in `modules/vlan.yml` for more details.
* **_required** (bool) -- the attribute must be present in the parent dictionary[^CRQ]
* **_valid_with** -- a list or dictionary of attributes that can be used with this attribute ([example](inter-attribute-examples)).
* **_invalid_with** -- specifies attributes that cannot be used together with this attribute. Can be:

  - A list of attribute names (this attribute cannot be used when any of the listed attributes are present)
  - A dictionary where keys are attribute names and values specify that the conflict occurs when the conflicting attribute has (one of the) the specified value(s)

* **_alt_types** -- [alternate data types](validation-alt-types)

[^CRQ]: This does not make the parent dictionary mandatory, but if it's present, it must have the required attribute. Use a chain of `_required` attributes if you want to enforce the presence of an attribute deep in the data structure.

See [](validation-definition-examples) and [](inter-attribute-examples) for more details.

### Further Data Type Validation Options

When an attribute has a data type defined with the **type** attribute, you can use the following attributes to perform value-based validations:

{.wrap-cells}
| Data type | Value validation option |
|-----------|-------------------------|
| **str**   | **valid_values** -- list of valid values |
| **list**  | **valid_values** -- list of valid values, checked for every element in the list |
|           | **create_empty** (bool) -- replace None value with an empty list |
|           | **make_list** (bool) -- force non-scalar values to become single-element lists |
|           | **split_lines** (bool) -- split multi-line string value into multiple list elements |
|           | **_subtype** -- validate values as belonging to the specified subtype |
| **dict**  | **create_empty** (bool) -- replace None value with an empty dictionary |
|           | **_keys** -- validation rules for individual dictionary keys. |
|           | **_subtype** -- validate values as belonging to the specified subtype |
|           | **_keytype** -- validate keys as belonging to the specified scalar type |
|           | **_list_to_dict** -- [value can be specified as a list](validation-list-to-dict) |
| **float** | **min_value** -- minimum parameter value |
|           | **max_value** -- maximum parameter value |
| **id**    | **max_length** -- maximum identifier length |
| **int**   | **min_value** -- minimum parameter value |
|           | **max_value** -- maximum parameter value |
| **ipv4**  | **use** -- [the use of IPv4 address/prefix](validation-ip-address) |
| **ipv6**  | **use** -- [the use of IPv6 address/prefix](validation-ip-address) |

**Notes**
* **_keys** attribute is rarely used in dictionary definitions. Using a [shortcut definition](validation-shortcut-type) is much better. See [examples](validation-definition-examples) for a counterexample.

You can also specify additional hints and help messages with an attribute:

| Keyword   | Meaning |
|-----------|---------|
| **_help** | Help displayed when a value does not match the data type.<br>Overrides the built-in help message |
| **_hint** | Additional hint(s) displayed together with an error message.<br>Use this attribute to explain what could be wrong |

(validation-error-type)=
### Error Data Type

Sometimes you want to display a very specific error message when encountering an invalid attribute. For example, the **config.inline** validation test attribute only works when the **[files](plugin-files)** plugin is enabled. You can use the **error** data type to catch such scenarios, for example:

```
_v_entry:                   # Validation entry
  config:
    inline:
      type: error
      _err_msg: Enable "files" plugin to use the "inline" configuration template
    _alt_types: [ str ]
```

You can also use the **error** data type as a **_subtype** definition when an attribute can have a dictionary value only under very specific conditions. For example, the node **config** attribute is usually a list but could be a dictionary if the lab topology uses the **files** plugin:

```
node:
  config: 
    type: dict
    _subtype:
      type: error
      _err_msg: Enable "files" plugin to use the inline node/group configuration template(s)
    _alt_types: [ list ]
```

The **error** data type can have two additional attributes:

* **_err_msg**: The text to display as a hint to the user
* **_err_hint**: A hint from the **defaults.hints** dictionary to display as an explanation of the error

(validation-definition-examples)=
### Data Type Definition Examples

VLAN ID is an integer between 1 and 4K. VXLAN ID is an integer between 1 and 16M. This is how they are defined in the **vlan** definition:

```
attributes:
  vlan:
    id: { type: int, min_value: 1, max_value: 4095 }
    vni: { type: int, min_value: 1, max_value: 16777215 }
```

BGP sessions is a dictionary of per-AF BGP session types. The value of **bgp.attributes.global.sessions** is defined as a dictionary which triggers recursive validation:

```
bgp.attributes:
  global:
    sessions:
      ipv4: [ ibgp, ebgp ]
      ipv6: [ ibgp, ebgp ]
```  

Topology name definition contains an error message that should be more useful than the generic 'identifier is...' message:

```
global:
  name: 
    type: id
    _help: |
      Topology name should be no longer than 16 characters. It should start with a letter
      and contain letters, underscores or numbers. netlab derives it from directory name
      when it's not specified in the lab topology file.
```

*clab* provider parameters include a **type** attribute, colliding with the validation **type** attribute. Valid *clab* attributes thus have to be specified with **_keys** dictionary:

```
clab.attributes:
  node:
    type: dict
    _keys:          # Make keys explicit to get around the 'type' attribute
      binds:
      kind: str
      config_templates:
      type: str
      cmd: str
      ...
```

The global **vlans** dictionary can be used only with the **vlan** module:

```
attributes:
  global:
    vlans:                        # vlans is a valid global parameter
      type: dict                  # It's a dictionary
      _requires: [ vlan ]         # ... that requires VLAN module
```

The global **vrfs** attribute is a dictionary of **vrf** definitions. The VRF names must be valid identifiers.

```
attributes:
  global:
    vrfs:                         # vrfs is a valid global parameter
      type: dict                  # It's a dictionary
      _subtype: vrf               # ... of VRF definitions
      _keytype: id                # ... where the VRF names must be valid identifiers
      _requires: [ vrf ]          # ... that requires VRF module
```

You can specify a list of BGP session types for the MPLS 6PE functionality. However, you can also specify a *True* value for the global **mpls.6pe** attribute to enable the feature. The *True* value gets translated into a default list (enable 6PE on IBGP sessions):

```
mpls:
  attributes:
    global:
      6pe: { type: list, true_value: [ ibgp ] }
```

(inter-attribute-examples)=
### Attribute Dependency Validation Examples

The **delete.community.list** in a routing policy entry cannot be used with any other **delete.community** attributes. **‌**

```
      delete:
        community:
          standard: list
          extended: list
          large: list
          list:
            type: str
            _valid_with: [ ]

```

The **set** or **delete** attributes of a routing policy cannot be used when the **action** attribute is set to **deny** (because the route is dropped anyway):

```
  attributes:
    rp_entry:                       # Define routing policy entry
      _description: Routing policy entry
      action:
        type: str
        valid_values: [ permit, deny ]
      set:
        _invalid_with: { action: deny }
        ...
      delete:
        _invalid_with: { action: deny }
        ...
```

(validation-shortcut-type)=
## Shortcut Data Type Definitions

_netlab_ supports several shortcuts that make type definitions easier to create and read:

* A data type definition that is a string is transformed into a dictionary with the **type** key.
* A data type definition that is a list will match a list value. The value of the data type definition is used as the list of valid values.
* A data type definition that is a dictionary without the **type** key will match a dictionary. Keys starting with '_' (data validation parameters) will be retained in the data type definition, and all other keys will be transferred into the `_keys` dictionary.

**String example**

```
device_name: str
```

Is transformed into:

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

Consider using user-defined data types if you use the same data structure in multiple places. You can define them in **defaults.attributes** and use them to validate any attribute.

```{note}
When using user-defined data types, you must specify them as a string value of a validated attribute. You cannot use user-defined data types as a value for **‌type** validation attribute.
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

You can use the `_namespace` attribute within the user-defined data types to add attributes from other objects. For example, as you can use link attributes in VLAN definitions, the **vlan** definition (see `modules/vlan.yml`) includes the `_namespace` attribute:

```
attributes:
  vlan:                           # Define the VLAN object type
    id: { type: int, min_value: 1, max_value: 4095 }
    vni: { type: int, min_value: 1, max_value: 16777215 }
    mode: { type: str, valid_values: [ bridge, irb, route ] }
    prefix:
    _namespace: [ link ]          # VLANs can include link attributes
```

(validation-alt-types)=
## Alternate Data Types

Some *netlab* attributes could take a dictionary value, alternate values (*True* usually meaning *use default*, or *None* meaning *I don't care, do what you want*), or a list of keys.

### Specifying Alternate Data Types

**_alt_types** list (commonly used within a dictionary of valid attributes) specifies alternate data types that can be used instead of the primary data type. The types in the **_alt_types** list cannot be user-defined data types.

**Example:** ***igp*.af** attribute can take a dictionary of address families, or it could be left empty (*None*) to tell *netlab* to use the address families defined on the node:

```
ospf:
  attributes:
    global:
      af:
        _alt_types: [ NoneType ]
        ipv4: bool
        ipv6: bool
```

**Example:** A link prefix could be a dictionary (containing IPv4/IPv6 values checked elsewhere), a string that could be an IPv4 or IPv6 prefix, or a boolean value.

```
attributes:
  link:
    prefix:
      type: dict
      _alt_types: [ bool, prefix_str ]
```

(validation-list-to-dict)=
### Dictionary Specified As a List

Some _netlab_ attributes that are supposed to be a dictionary can take a list value. That list value is transformed into a dictionary: list elements become dictionary keys, and a default value is used for the dictionary values. Add the **_list_to_dict** key to the attribute specification to validate such attributes. The **_list_to_dict** key specifies the default value used when converting a list into a dictionary.

**_list_to_dict** parameter is commonly used with address family parameters. For example, OSPF allows **ospf.af** parameter to be a list of enabled address families or a dictionary of address families with True/False values, for example:

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

(validation-ip-address)=
## IP Address Validation

**ipv4** and **ipv6** validators have a mandatory **use** parameter that can take the following values:

* **address** -- an IP address without a subnet mask
* **prefix** -- an IP prefix without the host bits.
* **host_prefix** -- a host IP address with a prefix length. It must include the host bits unless the prefix length is /31 or /32 for IPv4 or /127 or /128 for IPv6.
* **interface** -- an IP address specified on an interface. It can take an integer (offset within subnet), True (unnumbered) or False (disabled) value and does not have to include a prefix length. The missing prefix length is taken from the link IP prefix.
* **subnet_prefix** -- an IP prefix that must include prefix length/subnet mask. It can take a True (unnumbered) or False (disabled) value.
* **id** (IPv4 only) -- an IPv4 address or a 32-bit unsigned integer. Use **id** for parameters like OSPF areas, BGP cluster IDs, or router IDs.

The **ipv4** validator recognizes an additional **named** parameter. When set to **true**, the value of the attribute can be a [named prefix](named-prefixes).

(dev-valid-special-keys)=
## Special Attribute Dictionary Keys

The attribute dictionaries can contain these special keys:

* **_namespace**: a list of additional namespaces recognized within the object. For example, the **vlan** object can contain **link** attributes (see `netlab show attributes vlan --format yaml` for an example)
* **_description**: object description displayed in the **netlab show attributes** printout (see `netlab show attributes _v_entry --format yaml` for an example)
