.. Network Simulation Tools documentation master file, created by
   sphinx-quickstart on Sat Dec 12 17:27:51 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ipSpace.net Network Simulation Tools
====================================================

The `ipSpace.net network simulation tools <https://github.com/ipspace/netsim-tools>`_ will help you be more proficient once you decide to drop GUI-based network simulators and to build your labs using CLI and infrastructure-as-code principles.

The *netsim-tools* tools will help you:

* Describe high-level lab topology in YAML format without worrying about the specific implementation details
* Use the same lab topology with multiple virtualization providers (Virtualbox, KVM/libvirt, Docker containers)
* Create Vagrant configuration files and Ansible inventory from the lab topology

Based on your lab topology the :doc:`create-topology<create-topology>` script will:

* Create an IPv4 and IPv6 addressing plan for your lab
* Prepare all the necessary configuration files to start the lab

Once the lab is started you can use the :doc:`initial-config.ansible <configs>` Ansible playbook to:

* Deploy initial configurations (interfaces, IP addresses, usernames...) to your lab devices
* Configure OSPF, IS-IS, BGP and SR-MPLS in your lab.

When the lab is fully configured you could:

* Use the **connect.sh** script to connect to network devices via SSH or **docker exec**
* Use **config.ansible** playbook to deploy custom configuration snippets

Before shutting down your lab, you might want to run the **collect-config.ansible** playbook to
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
   tool-overview.md
   create-topology.md
   configs.md
..

.. toctree::
   :caption: Reference Materials
   :maxdepth: 2
   :hidden:

   topology-reference.md
   modules.md
   module-reference.md
   defaults.md
..

.. toctree::
   :caption: Release Notes
   :maxdepth: 2
   :hidden:

   release.rst
   contribute.md
..
