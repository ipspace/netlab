# Groups of Lab Devices (Nodes)

Network devices (nodes) used in a virtual lab are automatically grouped into platform-specific groups like *iosv* or *nxos*. You can use these groups or custom groups to:

* Set node attributes or Ansible group variables
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

## Custom Node Groups

Virtual lab topology can specify additional (custom) device groups in the **groups** top-level parameter. The **groups** parameter must be a dictionary with group names as dictionary keys. Dictionary values could be either a list of member nodes or a further dictionary specifying **members**:


```
---
defaults.device: iosv
  
nodes: [ a,b,c,d,e,f ]

groups:
  g1: [ a,b,c ]
  g2:
    members: [ d,e,f ]
```

The custom node groups are used to create additional groups in Ansible inventory file. You can use custom node groups in any **netlab** command that invokes an Ansible playbook.

For example, `netlab config mpls.j2 --limit g1` would deploy configuration template `mpls.j2` only on lab devices A, B and C.

## Custom Configuration Templates

You can building complex labs with functionality that is not yet part of *netlab* with the help of **[netlab config](netlab/config.md)** command that deploys custom configuration template to a set of lab devices. 

To make the deployment of custom configuration template(s) part of a regular lab creating process[^CC], use **config** group attribute that can specify either a single template or a list of templates.

[^CC]: ... once your configuration templates are thoroughly tested ;)

For example, to deploy `ospf-anycast-loopback.j2` template on members of `anycast` group and `mpls-ldp.j2` on all devices in your lab during the **[netlab up](netlab/up.md)** process, use the following topology file:

```
defaults:
  device: iosv

groups:
  anycast:
    members: [ a1, a2, a3 ]
    config: [ ospf-anycast-loopback.j2 ]
  all:
    config: [ mpls-ldp.j2 ]

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

The **config** parameter can also be specified on individual nodes, for example:

```
defaults:
  device: cumulus

module: [ ospf ]

nodes:
  s1:
  s2:
  s3:
    config: [ something-special.j2 ]

links: [ s1-s2, s2-s3 ]
```

```{tip}
A **netlab config** command is executed by **netlab up** process for every template in every **config** parameter, regardless of whether it's specified on a group or a node. Excessive use of **config** parameters might thus result in slower lab deployment.
```

## Group Variables

Group definition could include group variables in the **vars** element. Group variables are a dictionary of name/value pairs:

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

Group variables are stored in **group_vars** directory when **[netlab create](netlab/create.md)** creates an Ansible inventory from the topology file. They can be used as normal Ansible group variables, for example in a Jinja2 template specified in **netlab config** command.

## Changing Group Variables for Predefined Groups

If you want to set one or more Ansible facts for all devices in your lab, use **vars** element in **all** group:

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

You could also change group variables for auto-created platform groups. For example, to change the default username Ansible uses to connect to Cumulus VX nodes, use:

```
defaults.device: cumulus

nodes: [ a,b,c ]

groups.cumulus.vars.ansible_user: other
```

## Setting Node Data in Groups

Sometimes you'd like to set a node attribute for all members of a group. For example, in a BGP anycast scenario we should set **[bgp.advertise_loopback](module/bgp.md#advertised-bgp-prefixes)** to *false* on all anycast server -- they should advertise only the anycast prefix not individual loopback prefixes. 

While it's perfectly OK to set the desired attribute on individual nodes, it's much more convenient to set it in a group definition with the **node_data** attribute.

**node_data** group attribute contains a set of values that should be set on all members of the group. The data is [deep-merged](defaults.md#deep-merging) with the existing node data -- for example, you could set **bgp.advertise_loopback** attribute without affecting **bgp.as** attribute.

Using **node_data** functionality, a BGP anycast topology file becomes much more concise than it would have been otherwise:

```
defaults:
  device: iosv

module: [ bgp, ospf ]

bgp.as: 65000

groups:
  anycast:
    members: [ a1, a2, a3 ]
    node_data:
      bgp.as: 65001
      bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

### Using Group Node Data with VRFs and VLANs

VRFs and VLANs mentioned in **node_data.vrfs** or **node_data.vlans** will be defined as global (topology-wide) VRFs/VLANs. The VLAN ID/VNI or VRF RT/RD values will be copied from **node_data.vlans**/**node_data.vrfs** into global **vlans**/**vrfs**. As every VLAN  needs a unique ID/VNI (likewise for VRF RT/RD), you cannot define different ID/VNI or RT/RD values for the same VLAN/VRF in different groups.

Example:

```
module: [ vlan,ospf ]

groups:
  g1:
    members: [ r1, r2 ]
    node_data:
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

The above topology will:

* Create topology-wide *red* and *blue* VLANs.
* Auto-assign VLAN ID and VNI to those VLANs.
* Copy **node_data.vlans** into R1 and R2 (setting OSPF cost for VLAN interfaces)
* Merge the global **vlans** definitions into **nodes.r1.vlans** and **nodes.r2.vlans**, ensuring the VLANs on R1 and R2 have the correct VLAN ID/VNI.

```{tip}
As the **node_data** is copied into all nodes in a group, you'll get all VLANs/VRFs mentioned in **node_data** defined on all group members regardless of whether they actually use those VLANs/VRFs.
```

## Setting Device Type or List of Modules in Groups

Node device type (**device** attribute[^DVTRANS]) or the list of configuration modules (**module** attribute[^MDTRANS]) cannot be set within group **node_data**. Use **device** or **module** attribute at the group level to set them.

The following example uses this functionality to use Cumulus VX on routers advertising anycast IP address, and to use BGP as the only configuration module on those devices.

```
defaults:
  device: iosv

module: [ bgp, ospf ]
bgp.as: 65000

groups:
  anycast:
    members: [ a1, a2, a3 ]
    module: [ bgp ]
    device: cumulus
    node_data:
      bgp.as: 65001
      bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

Notes:

* You can use **device** or **module** attribute only on groups with static members.

[^DVTRANS]: Device type must be set very early in the topology transformation process to check whether the selected device supports the configuration modules enabled for a node.

[^MDTRANS]: Configuration modules have to be initialized before the **node_data** is copied into nodes to support automatic BGP groups. Modifying the list of node modules after the modules have been initialized would result in weird errors.

## Automatic BGP Groups

BGP module creates a group named *asnnn* where *nnn* is the AS number for every BGP AS present in the lab topology. The members of the group are all nodes in that autonomous system.

You can set inventory variables (with **vars** attribute), deployment templates (with **config** attribute) or node data (with **node_data** attribute) on an automatic BGP group, but you cannot specify static group members.

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
    node_data:
      bgp.advertise_loopback: false

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

## Specifying Groups in Nodes

You could specify a group or a list of groups a node belongs to in the **group** attribute of a node instead of specifying group members in **groups** topology. You can also combine the two ways of defining groups, for example:

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
* Adds node E to group g3. The group is automatically created the first time it's encountered in a node **group** list.
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

The hierarchical groups specified in a lab topology file are directly translated into Ansible inventory groups. The above example will generate the following data structure for group **g2** in Ansible inventory file:

```
g2:
  children:
    g1: {}
    g3: {}
  hosts:
    d: {}
```

### Node Data in Hierarchical Groups

When faced with a group hierarchy, **node_data** processing takes great care to use the node values specified in the most-specific group. Continuing the previous example, now with **node_data**:

```
groups:
  g1: 
    members: [ a,b ]
  g2:
    members: [ d,g1,g3 ]
    node_data:
      foo: bar
  g3:
    members: [ e ]
    node_data:
      foo: baz
```

* Nodes **a**, **b** and **d** (direct and indirect members of group **g2**) will have the node attribute **foo** set to **bar**.
* Node **e** (member of group **g3**) will have the node attribute **foo** set to **baz** -- **g3** overwrites the **foo** value set by the parent group **g2**.

**‌node_data** processing performs [deep dictionary merge](defaults.md#deep-merging) when an attribute specified in the group **‌node_data** and the current value of node attribute are both dictionaries, allowing you to specify various parts of the same dictionary in different groups, for example:

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
    node_data:
      bgp:
        as: 65000
  g3:
    members: [ e ]
    node_data:
      bgp:
        as: 65001
```

* Node **a** has **bgp.rr** set to *True* (direct node data) and **bgp.as** set to 65000 (attribute merged from **g2** node data).
* Nodes **b** and **d** have **bgp.as** set to 65000.
* Node **e** has **bgp.as** set to 65001 (deep merge results in value from **g2** being overwritten by value from **g3**).
* Nodes **c** and **f** do not have any BGP-related attributes

### Custom Configuration Templates in Hierarchical Groups

Custom configuration templates for individual nodes are built from configuration templates of all parent groups (starting with the least-specific parent group) plus node configuration templates. When using the following topology file...

```
nodes:
  a:
    config: [ a ]
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
    config: [ g2a, g2b ]
  g3:
    members: [ e ]
    config: [ g3 ]
```

... individual nodes get the following configuration templates:

| node | template                                |
|------|-----------------------------------------|
| a    | g2a, g2b (from g2 via g1), a (from a)   |
| b    | g2a, g2b (from g2 via g1)               |
| c    | none (it's not a member of any group)   |
| d    | g2a, g2b (from g2)                      |
| e    | g2a, g2b (from g2 via g3), g3 (from g3) |
| f    | none (it's not a member of any group)   |

If you want to remove one or more templates specified by parent groups from a node or a group, use **-_x_** to remove a specific parent template from the list or `-` to remove all parent templates, for example:

```
nodes:
  a:
    config: [ -g2b, a ]
  b:
    config: [ -, b ]
  c:
  d:
  e:
    config: [ -g1, e ]
  f:

groups:
  g1: [ a,b ]
  g2:
    members: [ d,g1,g3 ]
    config: [ g2a, g2b ]
  g3:
    members: [ e ]
    config: [ g3 ]
```

The following configuration templates would be applied to individual nodes in the above lab topology:

| node | template                                        |
|------|-------------------------------------------------|
| a    | g2a (from g2 via g1, g2b removed), a (from a)   |
| b    | all parent templates removed, b (from b).       |
| c    | none (it's not a member of any group)           |
| d    | g2a, g2b (from g2)                              |
| e    | g2a, g2b (from g2 via g3), g3 (from g3), -g1 is ignored, e (from e) |
| f    | none (it's not a member of any group)           |
