Release Notes
=============

**Release 26.02 (2026-02-11)**

* Support for [Kubernetes (KinD) clusters](plugin-kind) based on work by [@wnagele](https://github.com/wnagele)
* Layer-2 EVPN/VXLAN support on Cat8000v, IOL, IOLL2
* Containers can be [configured with Linux scripts or *containerlab* startup-config parameter](platform-config-mode) instead of with an Ansible playbook.
* **[netlab graph](netlab-graph)** command can create graphs from a subset of nodes or links

[More details](release-26.02) and [a tiny breaking change](release-26.02-breaking)

**Release 26.01.01 (2026-01-14)**

Release 26.01.01 is a bug-fix release [fixing](bug-fixes-26.01.01) the **[netlab status](netlab-status)** crash.

**Release 26.01 (2026-01-12)**

Release 26.01 introduces a major rewrite of the device configuration file generation process, making it fully independent of Ansible. Ansible is used solely for configuration deployment.

Other new features include:

* EVPN for VXLAN-over-IPv6
* The 'skip_config' [node attribute](node-attributes) can be used to deploy partially-provisioned labs
* Lightweight [netlab API HTTP server](netlab-api)

[More details](release-26.01) and [breaking changes](release-26.01-breaking)

**Release 25.12.03 (2025-12-13)**

Release 25.12.03 changes the **ansible_host** inventory parameter from hostname to IPv4 address for containers with SSH servers to address a change in *ansible-pylibssh* version 1.3.0 that prevented underscores in SSH hostnames.

[Bug fixes in release 25.12.03](bug-fixes-25.12.03)

**Release 25.12.01/02 (2025-12-05)**

Release 25.12.01 fixes [a stupid bug](bug-fixes-25.12.01) that crashed **netlab install**. Release 25.12.02 fixes the target containerlab release version (it wasn't one of my best days).

**Release 25.12 (2025-12-05)**

* Large BGP community lists, implemented on Arista EOS, FRR, and Junos. You can use standard- or large community lists in [routing policies](generic-routing-policies)
* Support Cisco ASAv in *vrnetlab* containers
* [Reread validation tests](netlab-validate-dev) from the lab topology file (if it was modified since the lab was started) every time you run the **[netlab validate](netlab-validate)** command
* The **shutdown** [link/interface attribute](link-attributes) can be used to start labs with interfaces turned off
* The **bgp.rr_mesh** parameter [controls IBGP sessions between BGP route reflectors](bgp-ibgp-sessions)

[More details](release-25.12) and [breaking changes](release-25.12-breaking)

**Release 25.11.01 (2025-11-18)**

Release 25.11.01 fixes [two bugs](bug-fixes-25.11.01) that could prevent the use of SR-OS/SR-SIM or some external tools.

**Release 25.11 (2025-11-12)**

* SRv6 support on Cisco IOS/XE
* RIPv2/RIPng support on OpenBSD thanks to Remi Locherer
* The **[netlab graph](netlab-graph)** command can generate PNG/SVG/JPEG/PDF graphs if you have D2 or Graphviz installed
* You can generate [reports](netlab-report) and [graphs](netlab-graph), or inspect transformed topology data without starting a lab
* You can use device-based groups (for example, **eos** or **frr** groups) to set node attributes.

[More details](release-25.11) and [breaking changes](release-25.11-breaking)

**Release 25.10 (2025-10-08)**

* You can use [wildcards or regular expressions](groups-members) to specify group- or **[as_list](bgp-aslist)** ASN/RR members.
* New device: container version of Cisco 8000v emulator (running IOS XR)
* [Graphing improvements](release-25.10-graph)
* Support for vJunosEVO release 24/25
* OSPFv2/v3 on OpenBSD
* OSPFv2/v3 interface parameters on IOS XR

[More details...](release-25.10)

**Release 25.09-post1 (2025-09-14)**

[Release 25.09-post1](release-25.09-post1) fixes the _netlab_ templating crash caused by breaking changes in Ansible core release 12.9.

**Release 25.09 (2025-09-07)**

* Link impairment (implemented with Linux *netem* queuing discipline) can be defined in [lab topology](links-netem) or configured/controlled with the **[netlab tc](netlab-tc)** command
* Configurable [IPv6 Router Advertisement](links-ra) parameters
* The [**files** plugin](plugin-files) allows you to store the content of short files (including custom configuration templates) directly in the lab topology
* New device: Nokia SR-SIM
* [Graphing](release-25.09-graph), [reporting](release-25.09-reports), and [performance/scalability](release-25.09-performance) improvements

[More details...](release-25.09)

**Release 25.07 (2025-07-14)**

* The [ospf.areas plugin](plugin-ospf-areas) supports OSPFv2 and OSPFv3 stub areas, NSSA areas, and area ranges.
* The [BGP routing policies](plugin-bgp-policy) plugin supports aggregate BGP routes
* The [BGP configuration module](module-bgp) supports BGP confederations
* The [evpn.multihoming](plugin-evpn-multihoming) plugin implements EVPN Ethernet Segment Identifiers and EVPN-based MLAG/multihoming
* Baseline OpenBSD support

[More details...](release-25.07)

**Release 25.06 (2025-06-11)**

* Discard [static routes](generic-routing-static)
* [Redistribution](routing_import) of [static routes](generic-routing-static) into OSPF, IS-IS, RIPv2, RIPng, and BGP
* Numerous new Nokia SR-OS [features](release-25.06-sros-features) and [bug fixes](release-25.06-sros-bug-fixes).
* LAG on Junos

[More details...](release-25.06)

For older releases, check the [release notes archive](release-archive.md).

```eval_rst
.. toctree::
   :caption: Individual release notes
   :maxdepth: 1

   release/26.02.md
   release/26.01.md
   release/25.12.md
   release/25.11.md
   release/25.10.md
   release/25.09.md
   release/25.07.md
   release/25.06.md
   release-archive.md
```   
