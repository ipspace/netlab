# Lab Topology Reference

The lab topology is described in a YAML file using a dictionary format. You could use [hierarchical attribute names](topology/hierarchy.md) as dictionary keys to make the topology file more readable.

The three major components that should be present in every topology file are:

* **nodes** -- [lab devices (nodes)](nodes.md)
* **links** -- [links between the lab devices](links.md)
* **defaults** -- topology-wide defaults like default device type

(topology-reference-top-elements)=
Other topology elements include:

* **addressing** -- [IPv4 and IPv6 pools](addressing.md) used to address management, loopback, LAN, P2P and stub interfaces
* **components** -- [reusable components](components.md) that you can include in multiple places in the lab topology
* **groups** -- optional [groups of nodes](groups.md)
* **module** -- default list of [modules](modules.md) used by this network topology. You can use device-level **module** attribute to override this setting for individual nodes.
* **plugin** -- list of [plugins](plugins.md) used by this topology.

Finally, you can set these topology-level parameters:

* **provider** -- virtualization provider (default: libvirt)
* **message** -- a help message to display after successful **[netlab initial](netlab/initial.md)** or **[netlab up](netlab/up.md)** commands. You can use that message to tell the end-user how to use the lab (example: [VLAN integration test cases](https://github.com/ipspace/netlab/tree/master/tests/integration/vlan)).
* **name** -- topology name (used in bridge names)

**Notes:**

* All elements apart from **nodes** are optional -- missing **links** element indicates a topology without inter-node links (just the management interfaces)
* Default values of **defaults** and **addressing** elements are taken from [default settings](defaults.md).
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
   providers.md
   components.md
   defaults.md
   topology/hierarchy.md
   extend-attributes.md
```
