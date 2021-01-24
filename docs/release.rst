Release notes
=============

2021-01-xx (`release 0.3 <https://github.com/ipspace/netsim-tools/releases/tag/release_0.3>`_)
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

Future plans
------------
Release 0.21
  Add support for per-node link data (example: OSPF priority)

  Add global custom parameters (example: OSPF reference bandwidth, BGP AS number)

Release 0.4
  Add network models (example: IGP, BGP + IGP)

.. toctree::
   :caption: Individual release notes
   :maxdepth: 2

   release/0.3.md
