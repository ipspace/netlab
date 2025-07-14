Release Notes
=============

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

**Release 2.0.1 (2025-05-23)**

Release 2.0.1 includes [bug](bug-fixes-2.0.1) and [documentation](doc-fixes-2.0.1) fixes as well as [minor device configuration improvements](release-2.0.1).

**Release 2.0.0 (2025-05-10)**

* Well-defined [node roles](node-router-host) (**host**, **router**, **bridge**) available on [multiple platforms](platform-host)
* **[firewall.zonebased](plugin-firewall-zonebased)** plugin
* **bridge** nodes can be used as [simple bridges](node-role-bridge) or to [implement multi-access links](node-bridge-lan)
* **[netlab defaults](netlab-defaults)** command provides **sysctl**-like CLI interface to user/system defaults.
* SRv6: [BGP L3VPN support](module-srv6)
* [VirtualBox and direct Windows/macOS installations](lab-virtualbox) are obsolete

[More details...](release-2.0.0)

**Release 1.9.6 (2025-03-21)**

* Add 'gateway' as a valid next-hop for [static routes](generic-routing-static)
* Rewrite the default gateway processing and add IPv6 default gateways
* [Set libvirt MTU to 9500](libvirt-network) on bridge-based networks

[More details...](release-1.9.6)

**Release 1.9.5 (2025-03-05)**

* Cumulus Linux NVUE: VXLAN, EVPN, VRF-aware BGP, VRF route leaking, route import
* Junos: BGP local-as, allowas-in, and EBGP multihop
* vJunos-switch: anycast gateway, VXLAN, and EVPN
* [VXLAN anycast VTEP in MLAG deployments](plugin-mlag-vtep)
* Use [configured node management MAC/IPv4 addresses](libvirt-mgmt-ip) in vagrant-libvirt DHCP pool
* Make `--instance` and `--snapshot` CLI parameters consistent 

[More details...](release-1.9.5)

**Release 1.9.4-post2 (2025-02-10)**

This release fixes [niche features in multiple configuration templates](release-1.9.4-post-2-device-fixes) and [a few bugs](bug-fixes-1.9.4-post2).

**Release 1.9.4-post1 (2025-02-03)**

This release fixes [a convoluted bug triggered by Arista EOS internal VLAN allocation](bug-fixes-1.9.4-post1) and [a few quirks in the configuration templates](release-1.9.4-post-1-device-fixes).

**[Release 1.9.4](release-1.9.4) (2025-01-29)**

Release 1.9.4 includes numerous [bug fixes](bug-fixes-1.9.4) and [fixes in device definitions and configuration templates](release-1.9.4-device-fixes).

**Release 1.9.3-post1 (2025-01-15)**

This release [fixes a few things we broke in 1.9.3](bug-fixes-1.9.3-post1) and [pins the version of `python-box`](https://github.com/ipspace/netlab/issues/1815).

**[Release 1.9.3](release-1.9.3) (2025-01-09)**

* Multi-chassis Link Aggregation (MLAG) support in the [](module-lag)
* [Generic object (node, VRF, VLAN) groups](topo-groups)
* Global, VRF, and inter-VRF [static routes](generic-routing-static) with direct or indirect next hops.
* [OSPF interface timers, cleartext passwords, and DR priority](ospf-interface-support)
* [Node cloning plugin](plugin-node-clone) simplifies repetitive topologies by cloning nodes
* [Consistent selection of prefix pools](links-default-pools) based on the number of nodes attached to a link (⚠️ [breaking change](release-1.9.3-breaking))

[More details...](release-1.9.3)

**Release 1.9.2-post1 (2024-12-10)**

This release [fixes an annoying bug](bug-fixes-1.9.2-post1) affecting users of Ansible 11.x.

**[Release 1.9.2](release-1.9.2) (2024-11-03)**

* [](module-stp)
* [](module-lag)
* The **[netlab exec](netlab-exec)** command can execute the same command on a set of network devices
* _netlab_ [supports](platform-devices) Cisco IOS on Linux (IOL), IOL layer-2 image, and IOSv/IOSvL2 in [*vrnetlab* containers](clab-vrnetlab)
* [Edgeshark](https://github.com/siemens/edgeshark) can be used [as an external tool](extool-edgeshark) to provide GUI-based access to lab packet capture

[More details...](release-1.9.2)

**[Release 1.9.1](release-1.9.1) (2024-10-05)**

* [**netlab capture**](netlab-capture) command implements packet capture on VM- or container interfaces
* IS-IS [route import](isis-node) ([redistribution](routing_import)) and [IS-IS VRF instances](isis-platform)
* RIPv2/Ripng [route import](rip-params) and [VRF instances](rip-vrf)
* [Configurable RIPv2/RIPng protocol timers](rip-timers)
* Support for [Cisco IOSv layer-2 image](https://developer.cisco.com/docs/modeling-labs/iosvl2/#iosvl2)

[More details...](release-1.9.1)

**[Release 1.9.0-post1](release-1.9.0-post1) (2024-08-26)**

This release contains [minor improvements](release-1.9.0-post1), numerous [SR Linux configuration fixes](release-1.9.0-post1-device-fixes), a few other [bug fixes](bug-fixes-1.9.0-post1), and [documentation fixes](doc-fixes-1.9.0-post1).

**[Release 1.9.0](release-1.9.0) (2024-08-19)**

* [](generic-routing) supporting routing policies, prefix filters, AS-path filters, and BGP community filters
* [Default route origination](ospf-default) in OSPFv2 and OSPFv3  
* [Route import](routing_import) (redistribution) into OSPFv2, OSPFv3, and BGP.
* [Named prefixes](named-prefixes)
* [Change device configuration](validate-config) or [use SuzieQ](validate-suzieq) in [validation tests](validate)
* [VRF multihop EBGP sessions](plugin-ebgp-multihop)

[More details...](release-1.9.0)

For older releases, check the [release notes archive](release-archive.md).

```eval_rst
.. toctree::
   :caption: Individual release notes
   :maxdepth: 1

   release/25.07.md
   release/25.06.md
   release/2.0.md
   release/1.9.md
   release-archive.md
```   
