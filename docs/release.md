Release Notes
=============

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

**Release 1.8.4-post2 (2024-07-13)**

This release contains only [bug fixes](bug-fixes-1.8.4-post2) and [documentation fixes](doc-fixes-1.8.4-post2).

**Release 1.8.4-post1 (2024-07-01)**

This release contains only [bug fixes](bug-fixes-1.8.4-post1) and [documentation fixes](doc-fixes-1.8.4-post1).

**[Release 1.8.4](release-1.8.4) (2024-06-22)**

* Support for [Cisco Catalyst 8000v](platform-devices)
* Unified support of [vrnetlab containers](clab-vrnetlab) (including ArubaCX, Cisco Catalyst 8000v, Cisco CSR 1000v, Dell OS10, Cisco Nexus 9000v, Mikrotik RouterOS, Juniper vMX, vPTX and vSRX)
* Automated build of [GitHub Codespaces devcontainer](https://github.com/users/ipspace/packages/container/package/netlab%2Fdevcontainer)
* Handle keyboard interrupts in long-running netlab commands, including **[netlab up](netlab-up)**, **[netlab initial](netlab-initial)** and **[netlab validate](netlab-validate)**.
* Add `--ready` action to **[netlab initial](netlab-initial)** command to wait for lab devices to become ready without configuring them.

[More details...](release-1.8.4)

**[Release 1.8.3](release-1.8.3) (2024-06-16)**

* [RIPv2/RIPng configuration module](module-ripv2)
* BGP Link Bandwidth community in [bgp.policy](plugin-bgp-policy) plugin
* BGP route server/client in [bgp.session](plugin-bgp-session) plugin.
* Installation scripts work with Ubuntu 24.04. They were also tested on Ubuntu 22.04, Ubuntu 20.04, and Debian Bookworm.

[More details...](release-1.8.3)

**[Release 1.8.2](release-1.8.2) (2024-05-13)**

* [Create reports](netlab-report) from a subset of nodes
* [Inspect](netlab-inspect) the same variable(s) [across multiple nodes](netlab-inspect-node)
* Check for the presence of Vagrant boxes or Docker containers before [starting the lab](netlab-up) and display pointers to build recipes.
* Check installed Ansible collections before starting **[netlab up](netlab-up)** or **[netlab initial](netlab-initial)**
* Support for [Sonic VM](platform-devices) based on Azure sonic-vs images.
* [Numerous improvements](release-1.8.2-vagrant) in the Vagrant box-building process

[More details...](release-1.8.2)

**Release 1.8.1-post1 (2024-04-24)**

This release contains only [bug fixes](bug-fixes-1.8.1-post1) and [documentation fixes](doc-fixes-1.8.1-post1).

**[Release 1.8.1](release-1.8.1) (2024-04-08)**

* Refactor the **[netlab status](netlab-status)** printout
* Add '[retry tests until the timeout](validate-retry)' functionality to **[netlab validate](netlab-validate)** (including the actual time it took to get the expected results).
* [OSPFv3 in VRFs](module-vrf-platform-routing-support), implemented on Arista EOS, Cisco IOS, Cisco IOS-XE, FRR, and Junos (vMX, vPTX, vSRX).
* [EBGP sessions over IPv4 unnumbered and IPv6 LLA interfaces](bgp-platform) on Arista EOS
* Cisco IOS XRd container support
* [Numerous configuration template fixes](release-1.8.1-device-fixes), including reduced OSPF SPF/LSA and IPv6 ND RA timers.

[More details...](release-1.8.1)

**[Release 1.8.0](release-1.8.0) (2024-03-01)**

* **netlab up** command can [reload saved device configurations](netlab-up-reload) instead of starting the initial device configuration process.
* [DHCP configuration module](module-dhcp) implements DHCP clients, DHCP servers, and DHCP relays for IPv4 and IPv6.
* Lab topology can include control plane- and network services [daemons](platform-daemons) running in Linux containers. This release includes BIRD and dnsmasq daemons.
* [BGP configuration module](module-bgp) supports 4-octet BGP AS numbers and [large BGP communities](bgp-community-propagation).
* [Validation plugins](validate-plugin) allow you to write more powerful **netlab validate** validation tests without creating complex Jinja2 templates
* You can build Docker containers for the [supported daemons](platform-daemons) with the **[netlab clab build](netlab-clab-build)** command

[More details...](release-1.8.0)

**Release 1.7.2 (2024-01-26)**

This release contains only [bug fixes](bug-fixes-1.7.2) and [documentation fixes](doc-fixes-1.7.2).

**[Release 1.7.1](release-1.7.1) (2024-01-08)**

* [Automatically create nodes from group members](groups-auto-create)
* [Add 'wait' parameter](validate-wait) to validation tests
* Use colors in netlab up/down/test/validate printouts
* Use color-coded error messages
* Use the **rich** Python library to pretty-print tables, JSON, and YAML

[More details...](release-1.7.1)

**[Release 1.7.0](release-1.7.0) (2023-12-03)**

* **[netlab validate](netlab/validate.md)** command can be used to execute [lab validation tests](topology/validate.md).
* The [**fabric** plugin](plugins/fabric.md) generates a whole leaf-and-spine fabric topology from a few parameters.
* The [**bgp.domain** plugin](plugins/bgp.domain.md) allows you to create topologies with multiple independent devices or sites using the same BGP AS number.
* The [**bgp.policy** plugin](plugins/bgp.policy.md) supports AS-path prepending on Arista EOS, Aruba AOS-CX, Cisco CSR 1000v, Cisco IOSv, Cumulus Linux, FRR
* [**bgp.originate** plugin](plugins/bgp.originate.md) uses loopbacks (instead of static routes to Null device) to originate BGP IPv4 and IPv6 prefixes
* The `--show` option of the **[netlab connect](netlab/connect.md)** command implements a consistent cross-device way of executing show commands.

[More details...](release-1.7.0)

For older releases, check the [release notes archive](release-archive.md).

```eval_rst
.. toctree::
   :caption: Individual release notes
   :maxdepth: 2

   release/2.0.md
   release/1.9.md
   release/1.8.md
   release/1.7.md
   release-archive.md
```   
