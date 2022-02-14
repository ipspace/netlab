Release notes
=============

2022-02-14 (release 1.1.3)
  * Restructured installation documentation
  * OSPFv3 support
  * netlab show command displays system settings in tabular format
  * EIGRP implementation of common routing protocol features
  * Configurable address family support (IPv4 and/or IPv6) for IS-IS, OSPF, and EIGRP
  * Libvirt box creating script for Cisco CSR 1000v and Juniper vSRX 3.0
  * Support for /31 IPv4 P2P links
  * Configurable MTU for VyOS and RouterOS

  :doc:`More details <release/1.1>`

2022-01-29 (release 1.1.2)
  * Containerlab installation script
  * System and interface MTU
  * Configurable VM memory and CPU settings
  * Configurable BGP cluster ID
  * Router ID calculations for IPv6-only devices and configurable router ID
  * Hosts and default gateways
  * Static loopback addresses
  * Cumulus Linux 5.0 support (configuration via NVUE)
  * BGP graphs can show RR-client sessions as directed arrows
  * Building vEOS and Nexus 9300v libvirt boxes has been significantly simplified with **netlab libvirt package** command
  * Proof-of-concept EVPN and SRv6 modules

  :doc:`More details <release/1.1>`

2022-01-20 (release 1.1.1)
  * Cumulus VX: unnumbered interfaces and support for EBGP sessions over unnumbered IPv4 interfaces
  * OVS bridge support in containerlab provider
  * Bug fixes

  :doc:`More details <release/1.1>`

2022-01-09 (release 1.1)
  * New IPAM functionality: layer-2-only links and interfaces, per-protocol unnumbered interfaces
  * IPAM code refactoring
  * BFD configuration module
  * BFD with IS-IS and OSPF
  * Device capability checks: unnumbered interfaces, OSPF and IS-IS over unnumbered links
  * Linux bridges are used to implement multi-access links in *containerlab*
  * Simplified IS-IS and OSPF configuration templates
  * Reorganized nodes list into a dictionary
  * Reorganized link interfaces into a list

  :doc:`More details <release/1.1>`

2021-12-28 (release 1.0.6)
  * Full SR Linux and SR OS support
  * Plugin packages and module extensions
  * Hierarchical device groups
  * Custom deployment templates moved to 'netlab initial'
  * Device-specific module attributes
  * Support for multi-access links in containerlab

  :doc:`More details <release/1.0>`

2021-12-19 (release 1.0.5)
  * Custom deployment templates for individual nodes
  * Support for vagrant-libvirt 0.7.0
  * Support for more than 10 lab devices under libvirt
  * Extendable topology-, link- and module parameters
  * Automatic creation of vagrant-libvirt management network
  * Bug fixes

  :doc:`More details <release/1.0>`

2021-12-11 (release 1.0.4)
  * Fortinet configuration (IPv4, IPv6, OSPF)
  * Links without IP addressing
  * IOSv, CSR, vSRX on VirtualBox
  * Bug fixes

  :doc:`More details <release/1.0>`

2021-12-06 (release 1.0.3)
  * Initial support for Fortinet devices
  * Skip devices that cannot be configured during lab initialization process
  * Bug fixes

  :doc:`More details <release/1.0>`
  
2021-11-27 (release 1.0.2)
  * Support for Mikrotik CHS and Vyos devices (contributed by Stefano Sasso)
  * Group-specific node data
  * Automatic creation of AS-based groups
  * Custom plugins

  :doc:`More details <release/1.0>`

2021-11-20 (release 1.0.1)
  * Custom inventory groups
  * Group-specific custom configuration templates
  * Composite command debugging
  * Quiet run of Ansible playbooks

  :doc:`More details <release/1.0>`

2021-10-25 (release 1.0)
  * **netlab up** enables *LLDP passthrough* on Linux bridges created with *libvirt* Vagrant plugin
  * Cleanup: remove the old CLI commands and related documentation

  :doc:`More details <release/1.0>`

2021-10-13 (release 0.9.3)
  * Add **netlab up** and **netlab down** commands
  * Add static node IDs and interface addresses

  :doc:`More details <release/0.9>`

2021-10-08 (release 0.9.2)
  * Add a simple YAML-based inventory file to replace **ansible_inventory** if you happen to hate Ansible.

  :doc:`More details <release/0.9>`

2021-09-19 (release 0.9.1)
  * End hosts in network labs (Linux VMs or containers)

  :doc:`More details <release/0.9>`

2021-08-20 (release 0.9)
  * Topology graphs (physical topology and BGP sessions)
  * YAML or JSON representation of transformed network topology
  * Generic output framework

  :doc:`More details <release/0.9>`

2021-07-09 (release 0.8)
  * Python package
  * Unified CLI
  * Support for Cumulus VX and Nokia SR Linux containers
  * Installation and testing scripts

  :doc:`More details <release/0.8>`

2021-05-31 (release 0.7)
  * EIGRP configuration module
  * BGP parameters: advertise_loopback, originate prefixes, community propagation
  * BGP IPv6 address family configuration
  * OSPF reference bandwidth
  * IS-IS P2P network type on all P2P links (not just unnumbered)
  * Single-module initial configuration
  * Python type hinting and mypy checks

  :doc:`More details <release/0.7>`

2021-05-24 (`release 0.6.3 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.6.3>`_)
  * BGP configuration module
  * IS-IS configuration module
  * Segment Routing with MPLS
  * OSPF configuration improvements: external links and passive interfaces
  * FRR and Cumulus VX support
  * Installation playbook
  * Bug fixes

  :doc:`More details <release/0.6>`

2021-04-11 (`release 0.5 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.5>`_)
  * containerlab support
  * Flexible virtualization provider framework

  :doc:`More details <release/0.5>`

2021-03-26 (`release 0.4 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.4>`_)
  * Unnumbered interfaces
  * Configuration modules framework
  * Baseline OSPF module

  :doc:`More details <release/0.4>`

2021-01-24 (`release 0.3 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.3>`_)
  * Support for multiple virtualization providers
  * Vagrant with VirtualBox
  * EOS and Nexus OS supported on Vagrant/VirtualBox
  * Device images (Vagrant boxes) are configurable in the defaults

  :doc:`More details <release/0.3>`

2021-01-12 (`release 0.2 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.2>`_)
   Major refactoring of addressing configuration

   * Structured address pools (loopback, lan, p2p)
   * IPv4 and IPv6 support
   * Initial configuration modules updated to work in dual-stack or IPv6-only environments

2021-01-07 (`release 0.11 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.11>`_)
   Arrcus ArcOS support contributed by Dave Thelen

   Refactored configuration gathering -- use explicit **device_facts** modules or platform-specific tasks
   for platforms that don't gather device configuration with fact-gathering module
2020-12-21
   Nexus 9300v support
2020-12-17
   Initial release (IOSv, CSR, EOS)

.. toctree::
   :caption: Individual release notes
   :maxdepth: 2

   release/1.1.md
   release/1.0.md
   release/0.9.md
   release/0.8.md
   release/0.7.md
   release/0.6.md
   release/0.5.md
   release/0.4.md
   release/0.3.md
..
