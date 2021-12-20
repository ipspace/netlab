# Groups of Lab Devices (Nodes)

Network devices (nodes) used in a virtual lab are automatically grouped into platform-specific groups like *iosv* or *nxos*. These groups could be used to limit the scope of **[netlab](netlab/cli.md)** commands that invoke Ansible playbooks. 

For example, you could use `netlab config mpls.j2 --limit iosv` to deploy configuration specified in Jinja2 template `mpls.j2` only on Cisco IOSv devices.

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

You can building complex labs with functionality that is not yet part of *netsim-tools* with the help of **[netlab config](netlab/config.md)** command that deploys custom configuration template to a set of lab devices. 

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

To make the definition a bit more concise, use the hierarchical names supported by *netsim-tools*:

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
