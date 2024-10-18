(custom-config)=
# Custom Configuration Templates

You can build complex labs with functionality that is [not yet part of *netlab*](netlab-customize) with the custom configuration templates that can be deployed with **[netlab config](netlab-config)**, **[netlab initial](netlab-initial)** or **[netlab up](netlab-up)** commands. The custom configuration templates could be stored in the lab topology directory, the user's defaults directory, or within the _netlab_ package. See [](dev-find-custom) for more details.

For a one-off deployment of custom configuration templates, use the **netlab config** command. To make the deployment of custom configuration template(s) part of a regular lab initialization process[^CC], use **config** group- or node attribute that can specify either a single template or a list of templates.

[^CC]: ... once your configuration templates are thoroughly tested ;)

For example, to deploy the `ospf-anycast-loopback.j2` template on members of the `anycast` group and `mpls-ldp.j2` on all devices in your lab during the **[netlab up](netlab/up.md)** process, use the following topology file:

```
defaults:
  device: iosv

groups:
  anycast:
    members: [ a1, a2, a3 ]
    config: [ ospf-anycast-loopback ]
  all:
    config: [ mpls-ldp ]

nodes: [ l1, l2, l3, s1, a1, a2, a3 ]
```

```{tip}
* You don't have to specify the `.j2` suffix in the names of custom configuration templates
* **‌config** attributes from multiple overlapping groups (_anycast_ and _all_ in the above example) are merged on nodes that belong to multiple groups.
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
    config: [ something-special ]

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

(custom-config-multivendor)=
## Multi-Vendor and Device-Specific Templates

If your configuration template specifies a Jinja2 file (without the `.j2` suffix), _netlab_ applies the same template to all devices using it.

You can, however, specify a directory name as the configuration template name. In that case, _netlab_ expects the directory to contain device- or platform-specific configuration templates:

* Use a node name with the `.j2` suffix to create a template that will be applied to a single node. For example, **r1.j2** will create the configuration for node **r1**.
* Use the _netlab_ device name to create a template that will be applied to a specific device type. For example, you could have **eos.j2** and **frr.j2** files in the configuration directory to create configurations for Arista EOS and FRRouting.
* You can use generic device types (for example, `ios` or `junos`) in template names to apply the same template to multiple platforms. For example, the configuration template **ios.j2** would generate configurations for IOSv, CSR 1000v, or Catalyst 8000v.
* You can be very specific and create templates that are applied to a single node when running a specific network operating system. For example, the **x1.eos.j2** template will be applied only to node X1 running Arista EOS.

While it's highly recommended to use a subdirectory to store the node- or platform-specific configuration templates, _netlab_ can also find templates that combine custom configuration, node, platform, and virtualization provider values. Use the **netlab show defaults paths.custom** command to display the exact combinations of node name (**inventory_hostname**), device names(**netlab_device_type**), Ansible network OS name (**ansible_network_os**), and virtualization provider (**node_provider**) used to find the custom configuration templates.

(custom-config-render)=
## Rendering Custom Configuration Templates

Custom configuration templates are Jinja2 templates. The Ansible playbook started by the **[netlab config](netlab-config)** or **[netlab initial](netlab-initial)** command uses the Jinja2 renderer to create device configurations that are then pushed to individual lab devices. For most network devices, the results of the Jinja2 rendering process are assumed to be the device configuration. The only exceptions are:

* Linux nodes, where the resulting configuration is assumed to be a **bash** script.
* Cumulus Linux or FRRouting nodes, where the resulting configuration is assumed to be **vtysh** configuration unless the first line of the configuration is `#!/bin/bash`, in which case the result is assumed to be a **bash** script.

You can use Ansible inventory variables in the custom configuration templates to generate flexible device configurations. For example, use this template if you want to enable BGP soft reconfiguration for all IPv4 BGP neighbors on a Cumulus Linux device:

```
router bgp {{ bgp.as }}
 !
 address-family ipv4 unicast
{% for n in bgp.neighbors if 'ipv4' in n %}
  neighbor {{ n.ipv4 }} soft-reconfiguration inbound
{% endfor %}
```

Execute **ansible-inventory --host _name_** or **netlab inspect --node _name_** to display all inventory variables you can use in a custom configuration template.
