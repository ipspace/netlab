(custom-config)=
# Custom Configuration Templates

You can build complex labs with functionality that is [not yet part of *netlab*](customize.md) with the custom configuration templates that can be deployed with **[netlab config](netlab/config.md)**, **[netlab initial](netlab/initial.md)** or **[netlab up](netlab/up.md)** commands. The custom configuration templates could be stored in the lab topology directory, the user's defaults directory, or within the _netlab_ package. See [](dev-find-custom) for more details.

For a one-off deployment of custom configuration templates, use the **netlab config** command. To make the deployment of custom configuration template(s) part of a regular lab initialization process[^CC], use **config** group- or node attribute that can specify either a single template or a list of templates.

[^CC]: ... once your configuration templates are thoroughly tested ;)

For example, to deploy the `ospf-anycast-loopback.j2` template on members of the `anycast` group and `mpls-ldp.j2` on all devices in your lab during the **[netlab up](netlab/up.md)** process, use the following topology file:

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

```{tip}
**‌config** attributes from multiple overlapping groups (_anycast_ and _all_ in the above example) are merged on nodes that belong to multiple groups.
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
Node **config** attributes are merged with the group **‌config** attributes. [Plugins](plugins.md) might append additional items to the node **‌config** attributes.
```

```{warning}
_netlab_ sorts custom configuration templates in the order specified in groups and nodes to speed up their deployment. Specifying `custom: [ a,b ]` on one node and `custom: [ b,a ]` on another will result in a sorting loop and a fatal error.
```

(custom-config-groups)=
## Custom Configuration Templates in Hierarchical Groups

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
