# Groups of Lab Objects (Nodes, VLANs, VRFs)

If you have several lab objects (nodes, VLANs, or VRFs) with similar attributes, use _netlab_ groups to apply a set of valid attributes to all of them.

You can define custom groups in lab topology or *netlab* defaults. *netlab* also creates node groups based on node devices (for example, *iosv* or *eos* group) and based on node **bgp.as** attribute (for example, *as65000* for all nodes with **bgp.as** set to 65000)

You can use custom- and netlab-created object groups to set node, VLAN, or VRF attributes. You can also use the node groups to:

* Set Ansible group variables
* Set device type or [configuration modules](module-reference.md) for a set of devices
* Attach additional configuration templates to a set of devices
* Limit the scope of **[netlab](netlab/cli.md)** commands that invoke Ansible playbooks.

For example, you could use `netlab config mpls.j2 --limit iosv` to deploy configuration specified in Jinja2 template `mpls.j2` only on Cisco IOSv devices.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(groups-create)=
## Creating Custom Object Groups

Lab topology can specify custom object groups in the **groups** top-level parameter. The **groups** parameter must be a dictionary with group names as dictionary keys. Dictionary values could be either a list of member nodes or a further dictionary specifying **members**:

```
---
defaults.device: iosv
  
nodes: [ a,b,c,d,e,f ]

groups:
  g1: [ a,b,c ]
  g2:
    members: [ d,e,f ]
```

The custom groups are assumed to contain nodes. To create a VLAN or a VRF group, set the group **type** to **vlan** or **vrf**, for example:

```
groups:
  ce_vlan:
    members: [ red_vlan, blue_vlan ]
    type: vlan
    ospf.cost: 1
    vlan.mode: route
  ce_vrf:
    members: [ red_vrf, blue_vrf ]
    type: vrf
    loopback: True
```

(default-groups)=
### Default Groups

You can specify system-wide or [project-wide](defaults-locations) groups in user- or system defaults file(s).

As expected, the default group settings are merged with the lab topology groups, and you can even use them to create new groups not defined in the lab topology.

The only peculiarity of the default groups is the handling of group members:

* Default groups can have a list of **members**
* A non-existent node in a group **members** list usually generates an error message. For default groups, such a member is silently removed from the **members** list[^DGM] (but see also [](groups-auto-create))
* The members of a default group are copied into the lab topology group only when the corresponding lab topology group has no members.

[^DGM]: That makes it possible to have default group members not present in the lab topology.

(groups-object-data)=
## Setting Object Data in Groups

Sometimes, you'd like to set an attribute for all group members. For example, in a BGP anycast scenario, we should set **[bgp.advertise_loopback](module/bgp.md#advertised-bgp-prefixes)** to *false* on all anycast server -- they should advertise only the anycast prefix, not individual loopback prefixes. 

While it's perfectly OK to set the desired attribute(s) on individual nodes, it's much more convenient to specify them in a group definition -- you can use any valid node, VLAN, or VRF attribute (including configuration module attributes[^MNA]) in group definitions[^NDT].

[^MNA]: If a node group definition contains a **module** attribute, you cannot set attributes for modules not listed in the **module** attribute in the group definition. VLAN and VRF groups can use only modules specified in the topology-level **module** attribute.
 
[^NDT]: Node attributes were stored in **node_data** group attribute prior to *netlab* release 1.4. While you can still use the **node_data** dictionary, it has a few undesired side effects that we'll not fix. It is deprecated in release 1.8; using it will generate a warning during the data transformation phase.

The group attributes will be set on all members of the group. The data is [deep-merged](defaults-deep-merging) with the existing object data -- for example, you could set **bgp.advertise_loopback** attribute in group definition without affecting **bgp.as** node attribute[^NDGP].

[^NDGP]: In a topology with [hierarchical groups](groups-hierarchy), attributes from the innermost groups take precedence. Node attributes from groups with static members have precedence over node attributes from BGP-generated groups.

Using this functionality, a BGP anycast topology file becomes much more concise than it would have been otherwise:

```
defaults:
  device: iosv

module: [ bgp, ospf ]

bgp.as: 65000

groups:
  anycast:
    members: [ a1, a2, a3 ]
    bgp.as: 65001
    bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

(groups-node-vlan-vrf)=
### Specifying VLANs and VRFs in Node Groups

VRFs and VLANs mentioned in a node group's **vrfs** or **vlans** attributes become global (topology-wide) VRFs/VLANs. The VLAN ID/VNI or VRF RT/RD values (when specified) are copied from the **vlans**/**vrfs** group data into global **vlans**/**vrfs** dictionaries. Every VLAN needs a unique ID/VNI (likewise for VRF RT/RD), so you cannot define different ID/VNI or RT/RD values for the same VLAN/VRF in multiple groups.

Example:

```
module: [ vlan,ospf ]

groups:
  g1:
    members: [ r1, r2 ]
    vlans:
      red:
        ospf.cost: 10
      blue:
        ospf.cost: 20

nodes: [r1, r2]

links:
- r1:
  r2:
  vlan.trunk: [ red, blue ]
```

The above topology:

* Creates topology-wide *red* and *blue* VLANs.
* Auto-assigns VLAN ID and VNI to those VLANs.
* Copies group **vlans** into R1 and R2 (setting OSPF cost for VLAN interfaces)
* Merges the global **vlans** definitions into **nodes.r1.vlans** and **nodes.r2.vlans**, ensuring the VLANs on R1 and R2 have the correct VLAN ID/VNI.

```{tip}
As the group VLANs/VRFs are copied into all nodes in a group, you'll get all VLANs/VRFs (and VLAN interfaces) mentioned in the group definition defined on all group members regardless of whether they use those VLANs/VRFs.
```

(groups-device-module)=
### Setting Device Type or List of Modules in Node Groups

You can set node device type (**device** attribute) or the list of configuration modules (**module** attribute) in a node group definition, but only on groups with static members.

The device type is copied from a group definition to member nodes with no **device** attribute. Modules listed in a group are added to the member node **module** attribute. The merging of node- and group modules takes precedence over the global (topology-level) list of modules.

The following example uses this functionality to:

* Use Cumulus VX on routers advertising an anycast IP address,
* Specify BGP as the only configuration module on those devices.

```
defaults.device: iosv

module: [ bgp, ospf ]
bgp.as: 65000

groups:
  anycast:
    members: [ a1, a2, a3 ]
    module: [ bgp ]
    device: cumulus
    bgp.as: 65001
    bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

**Notes:**
* _netlab_ adds the BGP module specified in the **anycast** group to the list of modules of individual group members. No group members have an explicit module definition, resulting in `module: [ bgp ]` being set on A1, A2, and A3.
* Device type specified in the **anycast** group is copied into A1, A2, and A3.
* Default device type specified in **defaults.device** is copied into nodes that still have no device type (L1, L2, L3, S1)
* Default list of modules (`module: [ bgp, ospf ]`) is copied into nodes that still have no **module** attribute (L1, L2, L3, S1).

(groups-ansible-inventory)=
## Netlab Groups in Ansible Inventory

The custom node groups are used to create additional groups in the Ansible inventory file. You can use custom node groups in any **netlab** command that invokes an Ansible playbook.

For example, given the following lab topology, `netlab config mpls.j2 --limit g1` would deploy configuration template `mpls.j2` only on lab devices A, B, and C.

```
---
defaults.device: iosv
  
nodes: [ a,b,c,d,e,f ]

groups:
  g1: [ a,b,c ]
  g2:
    members: [ d,e,f ]
```

(group-ansible-vars)=
### Ansible Group Variables

A node group definition could include Ansible group inventory variables in the **vars** element (a dictionary of name/value pairs). The following example creates two groups (g1 and g2) and sets Ansible group variables on g2.

```
---
defaults.device: iosv
  
nodes: [ a,b,c,d,e,f ]

groups:
  g1: [ a,b,c ]
  g2:
    members: [ d,e,f ]
    vars:
      x1: 1
      x2: 2
```

Group variables are stored in **group_vars** directory when **[netlab create](netlab/create.md)** creates an Ansible inventory from the topology file. The Ansible inventory group variables can then be used in Ansible playbooks and related Jinja2 templates, for example, in the [custom configuration templates](custom-config-templates.md) deployed with the **[netlab initial](netlab/initial.md)** or **[netlab config](netlab/config.md)** commands.

```{warning}
* Use this functionality only when you need custom attributes in Jinja2 templates but don't want to specify them as [valid node attributes](extend-attributes.md).
* You cannot use Ansible group variables to overwrite node data specified in a custom group. The [group node data](groups-object-data) is copied into the node data and stored in Ansible host variables.
* Ansible inventory is not used in the **[‌netlab connect](netlab/connect.md)** command. To overwrite connection-specific variables (connection method, username, password), specify `ansible_something` or `netlab_something` variables in node data. See [Node Attributes](node-ansible-data) for more details.
```

(group-special-names)=
### Special Ansible Group Names

The following groups have special meaning in *netlab*-generated Ansible inventory:

* `unprovisioned`: **netlab up** and **netlab initial** will skip devices in this group while deploying device configurations.

### Changing Group Variables for Predefined Groups

If you want to set one or more Ansible facts for all devices in your lab, use the **vars** element in the **all** group:

```
defaults.device: cumulus

nodes: [ a,b,c ]

groups:
  all:
    vars:
      http_server: true
```

To make the definition a bit more concise, use the *netlab* hierarchical attribute names:

```
defaults.device: cumulus

nodes: [ a,b,c ]

groups.all.vars.http_server: true
```

You could also change group variables for auto-created device-specific groups. For example, to change the default username used to connect to Cumulus VX nodes, use:

```
defaults.device: cumulus

nodes: [ a,b,c ]

groups.cumulus.vars.ansible_user: other
```

## Automatic BGP Groups

The BGP module creates a node group named *asnnn* where *nnn* is the AS number for every BGP AS present in the lab topology. The members of the group are all nodes in that autonomous system.

You can set inventory variables (with **vars** attribute), deployment templates (with **config** attribute), or node data on an automatic BGP group, but you cannot specify static group members.

Here is a BGP anycast topology file that depends on setting node data within an automatic BGP group (the topology file uses [BGP as-list](module/bgp.md#global-bgp-configuration-parameters) functionality to specify AS membership):

```
defaults:
  device: iosv

module: [ bgp, ospf ]

bgp:
  as_list:
    65000:
      members: [ l1, l2, l3, s1 ]
      rr: [ s1 ]
    65001:
      members: [ a1, a2, a3 ]

groups:
  as65001:
    bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

## Specifying Groups in Nodes

You could specify a group or a list of groups a node belongs to in the **group** attribute of a node instead of specifying group members in the **groups** topology attribute. You can also combine the two ways of defining groups, for example:

```
defaults:
  device: cumulus
  
nodes:
  a:
    group: [ g2 ]
  b:
  c:
  d:
  e:
    group: [ g2, g3 ]
  f:
    group: g1 

groups:
  g1: [ a,b,c ]
  g2:
    vars:
      x1: 1
      x2: 2
```

The above topology file:

* Creates two groups (g1 and g2) from the **groups** element.
* Adds nodes A and E to group g2. The **members** list is automatically created when the first node is added to the group.
* Adds node E to group g3. The group is automatically created the first time a node **group** list mentions it.
* Adds F to group g1. Please note that the **group** node attribute could be a string or a list of strings.

The final value of the **groups** element is thus:

```
groups:
  g1:
    members:
    - a
    - b
    - c
    - f
  g2:
    members:
    - a
    - e
    vars:
      x1: 1
      x2: 2
  g3:
    members:
    - e
```

(groups-hierarchy)=
## Hierarchical Groups

*netlab* supports _hierarchical groups_ -- groups could be members of other groups, for example:

```
nodes: [ a,b,c,d,e,f ]

groups:
  g1:
    members: [ a,b ]
  g2:
    members: [ d,g1,g3 ]
  g3:
    members: [ e ]
```

The hierarchical groups specified in a lab topology file are directly translated into Ansible inventory groups. The above example will generate the following data structure for group **g2** in the Ansible inventory file:

```
g2:
  children:
    g1: {}
    g3: {}
  hosts:
    d: {}
```

### Object Data in Hierarchical Groups

When faced with a group hierarchy, processing of object (node, VLAN, or VRF) data takes great care to use the object values specified in the most specific group (see also [](custom-config-groups))

Continuing the previous example, now with node data in groups[^FINV]:

[^FINV]: Please note that **foo** is not a valid node attribute.

```
groups:
  g1: 
    members: [ a,b ]
  g2:
    members: [ d,g1,g3 ]
    foo: bar
  g3:
    members: [ e ]
    foo: baz
```

* Nodes **a**, **b** and **d** (direct and indirect members of group **g2**) will have the node attribute **foo** set to **bar**.
* Node **e** (member of group **g3**) will have the node attribute **foo** set to **baz** -- **g3** overwrites the **foo** value set by the parent group **g2**.

Group data processing performs [deep dictionary merge](defaults-deep-merging) when an attribute specified in the group ‌and the current value of the member attribute are both dictionaries, allowing you to define various parts of the same data structure in different groups, for example:

```
nodes:
  a:
    bgp:
      rr: true
  b:
  c:
  d:
  e:
    config: [ e ]
  f:

groups:
  g1: [ a,b ]
  g2:
    members: [ d,g1,g3 ]
    bgp:
      as: 65000
  g3:
    members: [ e ]
    bgp:
      as: 65001
```

* Node **a** has **bgp.rr** set to *True* (direct node data) and **bgp.as** set to 65000 (attribute merged from **g2** node data).
* Nodes **b** and **d** have **bgp.as** set to 65000.
* Node **e** has **bgp.as** set to 65001 (deep merge results in value from **g2** being overwritten by value from **g3**).
* Nodes **c** and **f** do not have any BGP-related attributes

(groups-auto-create)=
## Create Objects From Group Members

To prevent typos and duplicate names, the group **members** attribute must contain valid group-type-specific object names specified in the **nodes**, **vlans**, or **vrfs** dictionary. However, if a group contains **\_auto\_create**  attribute set to *True*, *netlab* creates missing objects from group members. You can set the **\_auto\_create** attribute:

* In individual groups. You can specify the **\_auto\_create** attribute in individual default groups to create nodes in all labs using those defaults.
* In **groups** or **defaults.groups** dictionary. The global **\_auto\_create**  attribute does not apply to default groups.

For example, due to the global **\_auto\_create** attribute, the following topology creates nodes from the members of all topology groups (**g3**). It also creates nodes from the members of the **g2** default group due to the group **\_auto\_create** attribute.

```
defaults:
  device: cumulus
  
defaults.groups:
  g1:
    members: [ A, B ]
  g2:
    _auto_create: True
    members: [ C, D ]
    device: eos

groups:
  _auto_create: True
  g3: [ E, F ]
```

The lab will contain nodes **C** and **D** running Arista EOS and nodes **E** and **F** running Cumulus Linux.