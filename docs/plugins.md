(topo-plugins)=
# netlab Plugins

*netlab* supports dynamically loadable plugins, allowing you to implement custom data model transformations or other functionality without adding nerd knobs to the core topology transformation. You can [use plugins shipped with _netlab_](topo-plugins-builtin) or [write your own plugins](dev/plugins.md):

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using Plugins

Plugins needed by a topology file are listed in the **plugin** top-level element, for example:

```
plugin: [ bgp.session ]

module: [ ospf, bgp ]
```

You can specify additional (system-wide) plugins in [system defaults](topo-defaults) (**defaults.plugin**) or as a CLI parameter in **[netlab create](netlab/create.md)** or **[netlab up](netlab/up.md)** commands.

Plugins can define their own _netlab_ attributes that you can use to configure plugin-provided functionality. For example, the [BGP sessions](plugins/bgp.session.md) plugin defines **bgp.password** attribute that can be used to enable MD5 authentication of EBGP sessions:

```
---
provider: clab
defaults.device: eos
module: [ bgp ]
plugin: [ bgp.session ]

nodes:
  r1:
    bgp.as: 65101
  r2:
    bgp.as: 65000

links:
- r1:
  r2:
  bgp.password: Test
```

Plugins providing support for additional networking features usually rely on Jinja2 templates to configure those features, limiting their use to a subset of supported platforms. Please check the plugin documentation for more details.

(topo-plugins-builtin)=
## _netlab_ Built-In Plugins

These plugins are included with _netlab_ and can be used in all lab topologies:

```eval_rst
.. toctree::
   :caption: Routing Protocol Plugins
   :titlesonly: 

   plugins/bgp.domain.md
   plugins/bgp.session.md
   plugins/bgp.policy.md
   plugins/ebgp.multihop.md
   plugins/bgp.originate.md
   plugins/ospf.areas.md
   plugins/vrrp.version.md
```

```eval_rst
.. toctree::
   :caption: Data Plane and Multihoming Plugins
   :titlesonly: 

   plugins/bonding.md
   plugins/firewall.zonebased.md
   plugins/mlag.vtep.md
   plugins/evpn.multihoming.md
```

```eval_rst
.. toctree::
   :caption: Topology- and Lab Scaling Plugins
   :titlesonly: 

   plugins/fabric.md
   plugins/multilab.md
   plugins/multiserver.md
   plugins/node.clone.md
```

```eval_rst
.. toctree::
   :caption: Other Plugins
   :titlesonly: 

   plugins/check.config.md
   plugins/files.md
   plugins/kind.md
```

## More Information

* [](dev-plugins)
* [](dev-transform)
