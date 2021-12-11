# Lab Topology Reference

The lab topology is described in a YAML file using a dictionary format. The three major components that should be present in every topology file are:

* **nodes** -- [list of nodes](nodes.md)
* **links** -- [list of links](links.md)
* **defaults** -- describing topology-wide defaults like default device type

Other topology elements include:

* **provider** -- virtualization provider (default: libvirt)
* **groups** -- optional [groups of nodes](groups.md)
* **module** -- list of [modules](modules.md) used by this network topology
* **addressing** -- [IPv4 and IPv6 pools](addressing.md) used to address management, loopback, LAN, P2P and stub interfaces
* **name** -- topology name (used in bridge names)

**Notes:**

* All elements apart from **nodes** are optional -- missing **links** element indicates a topology without inter-node links (just the management interfaces)
* Default values of **defaults** and **addressing** elements are taken from default settings.
* List of modules is used to specify additional initial configuration elements (example: OSPF routing)
* Default topology name is the directory name.

You'll find sample topology files in the [tutorials](tutorials.md).

```eval_rst
.. toctree::
   :caption: Topology Components
   :maxdepth: 2

   nodes.md
   links.md
   groups.md
   addressing.md
   modules.md
   plugins.md
   defaults.md
```
