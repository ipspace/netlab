ipSpace.net Network Simulation Tools
====================================================

The `ipSpace.net network simulation tools <https://github.com/ipspace/netsim-tools>`_ will help you be more proficient once you decide to drop GUI-based network simulators and build your labs using CLI and infrastructure-as-code principles.

*netsim-tools* will help you:

* Describe high-level lab topology in YAML format without worrying about the specific implementation details
* Use the same lab topology with multiple virtualization providers (Virtualbox, KVM/libvirt, Docker containers)
* Create Vagrant configuration files and Ansible inventory from the lab topology

Based on your lab topology the :doc:`netlab create<netlab/create>` command will:

* Create an IPv4 and IPv6 addressing plan for your lab
* Prepare all the necessary configuration files to start the lab

Once the lab is started you can use the :doc:`netlab initial <netlab/initial>` command to:

* Deploy initial configurations (interfaces, IP addresses, usernames...) to your lab devices
* Configure OSPF, IS-IS, BGP and SR-MPLS in your lab.

When the lab is fully configured you could:

* Use the **netlab connect** command to connect to network devices via SSH or **docker exec**
* Use **netlab config** command to deploy custom configuration snippets

Before shutting down your lab, you might want to run the **netlab collect** command to
save the configuration changes you made.

Getting Started
---------------

* Explore the :doc:`supported platforms <platforms>` to figure out whether you could build your desired lab with *netsim-tools*
* Read the :doc:`installation guide <install>`
* Choose the virtualization method you'd like to use to build your lab
* Follow the `instructions in the installation guide <install.html#building-the-lab-environment>`_ to build your lab environment

.. toctree::
   :caption: Installation Guides
   :maxdepth: 2
   :hidden:

   install.md
   platforms.md
..

.. toctree::
   :caption: Using the Tools
   :maxdepth: 2
   :hidden:

   tutorials.md
   topology-overview.md
   cli-overview.md
..

.. toctree::
   :caption: Reference Materials
   :maxdepth: 1
   :hidden:

   netlab/cli.md
   topology-reference.md
   modules.md
   module-reference.md
   defaults.md
   outputs/index.md
..

.. toctree::
   :caption: Release Notes
   :maxdepth: 2
   :hidden:

   release.rst
   contribute.md
   legacy-cli/legacy.md
..
