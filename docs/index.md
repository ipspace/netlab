# netlab: a Virtual Networking Labbing Tool

*netlab* will help you be more proficient once you decide to drop GUI-based virtual networking labs and build your labs using CLI and infrastructure-as-code principles.

Using *netlab* you can:

* Describe high-level lab topology in YAML format without worrying about the specific implementation details
* Use the same lab topology with multiple virtualization providers (Virtualbox, KVM/libvirt, Docker containers)
* Create Vagrant- and containerlab configuration files and Ansible inventory from the lab topology
* Configure IP addressing, routing protocols, VLANs, VRFs, and other networking technologies in your lab

Based on your lab topology the **[netlab up](netlab/up.md)** command will:

* Create IPv4 and IPv6 addressing plan and OSPFv2, OSPFv3, EIGRP, IS-IS, BGP, MPLS/VPN, and EVPN routing design
* Prepare all the necessary configuration files to start the lab
* Start the lab using Vagrant or containerlab
* Create additional virtual networking infrastructure needed to support your lab
* Deploy initial configurations (interfaces, IPv4 and IPv6 addresses, usernames...) to your lab devices
* Configure VLANs, VRFs, VXLAN, LLDP, BFD, OSPFv2, OSPFv3, EIGRP, IS-IS, BGP, VRRP, anycast gateways,
  MPLS, BGP-LU, L3VPN (VPNv4 + VPNv6), 6PE, EVPN, SR-MPLS, or SRv6 on your lab devices.
* Start external network management tools specified in lab topology like Graphite or SuzieQ

When the lab is fully configured, you can:

* Use the **[netlab connect](netlab/connect.md)** command to connect to network devices via SSH or **docker exec**
* Use the **[netlab config](netlab/config.md)** command to deploy custom configuration snippets

Before shutting down your lab with the **[netlab down](netlab/down.md)** command, you might want to run the **[netlab collect](netlab/collect.md)** command to save the configuration changes you made.

## Getting Started

* Explore the [supported platforms](platforms.md) to figure out whether you could build your desired lab with *netlab*
* Read the [installation guide](install.md)
* Choose the virtualization method you'd like to use to build your lab
* Follow the [instructions in the installation guide](lab) to build your lab environment

More information
----------------
* After installing *netlab* you might want to [follow the tutorials](tutorials.md)
* Read the [blog posts](https://blog.ipspace.net/tag/netlab.html)_ describing *netlab* features and use cases
* Explore [BGP configuration labs](https://bgplabs.net) built with *netlab*
* Need even more examples? You'll find them in  [netlab examples repository](https://github.com/ipspace/netlab-examples)
* [Sample topology files](https://github.com/ipspace/netlab/tree/dev/tests/integration) we're using for integration testing might also be interesting
* Want to see the source code? It's [on GitHub](https://github.com/ipspace/netlab)
* Want to ask a question or report a bug? Open a [discussion](https://github.com/ipspace/netlab/discussions) or [an issue](https://github.com/ipspace/netlab/issues) in the [netlab GitHub repository](https://github.com/ipspace/netlab).

```eval_rst
.. toctree::
   :caption: Installation Guides
   :maxdepth: 2
   :hidden:

   install.md
   platforms.md
..
```

```eval_rst
.. toctree::
   :caption: Using the Tools
   :maxdepth: 2
   :hidden:

   tutorials.md
   topology-overview.md
   cli-overview.md
   example/addressing-tutorial.md
   example/vrf-tutorial.md
   example/external.md
..
```

```eval_rst
.. toctree::
   :caption: Reference Materials
   :maxdepth: 1
   :hidden:

   netlab/cli.md
   topology-reference.md
   modules.md
   module-reference.md
   providers.md
   defaults.md
   outputs/index.md
   customize.md
..
```

```eval_rst
.. toctree::
   :caption: Release Notes
   :maxdepth: 2
   :hidden:

   release.md
   caveats.md
..
```

```eval_rst
.. toctree::
   :caption: Developers
   :maxdepth: 2
   :hidden:

   dev/guidelines.md
   dev/plugins.md
   dev/config/index.md
   dev/advanced.md
   roadmap/index.md
..
```
