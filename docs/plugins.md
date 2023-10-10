# netlab Plugins

*netlab* supports dynamically loadable plugins allowing you to implement custom data model transformations or other functionality without adding nerd knobs to the core topology transformation. You might want to [write your own plugins](dev/plugins.md) or use plugins shipped with _netlab_:

```eval_rst
.. toctree::
   :maxdepth: 1

   plugins/bgp.session.md
   plugins/ebgp.multihop.md
   plugins/multilab.md
```

Plugins needed by a topology file are listed in the **plugin** top-level element, for example:

```
plugin: [ bgp.session ]

module: [ ospf, bgp ]
```

You can specify additional (system-wide) plugins in [system defaults](defaults.md) (**defaults.plugin**) or as a CLI parameter in **[netlab create](netlab/create.md)** or **[netlab up](netlab/up.md)** commands.

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

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: More information

   dev/plugins.md
```
