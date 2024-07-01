Release Notes
=============

**Release 1.8.4-post1 (2024-07-01)**

This release contains only [bug fixes](bug-fixes-1.8.4-post1) and [documentation fixes](doc-fixes-1.8.4-post1).

**[Release 1.8.4](release-1.8.4) (2024-06-22)**

* Support for [Cisco Catalyst 8000v](platform-devices)
* Unified support of [vrnetlab containers](clab-vrnetlab) (including ArubaCX, Cisco Catalyst 8000v, Cisco CSR 1000v, Dell OS10, Cisco Nexus 9000v, Mikrotik RouterOS, Juniper vMX, vPTX and vSRX)
* Automated build of [GitHub Codespaces devcontainer](https://github.com/users/ipspace/packages/container/package/netlab%2Fdevcontainer)
* Handle keyboard interrupts in long-running netlab commands, including **[netlab up](netlab-up)**, **[netlab initial](netlab-initial)** and **[netlab validate](netlab-validate)**.
* Add `--ready` action to **[netlab initial](netlab-initial)** command to wait for lab devices to become ready without configuring them.

**[Release 1.8.3](release-1.8.3) (2024-06-16)**

* [RIPv2/RIPng configuration module](module-ripv2)
* BGP Link Bandwidth community in [bgp.policy](plugin-bgp-policy) plugin
* BGP route server/client in [bgp.session](plugin-bgp-session) plugin.
* Installation scripts work with Ubuntu 24.04. They were also tested on Ubuntu 22.04, Ubuntu 20.04, and Debian Bookworm.

[More features...](release-1.8.3)

**[Release 1.8.2](release-1.8.2) (2024-05-13)**

* [Create reports](netlab-report) from a subset of nodes
* [Inspect](netlab-inspect) the same variable(s) [across multiple nodes](netlab-inspect-node)
* Check for the presence of Vagrant boxes or Docker containers before [starting the lab](netlab-up) and display pointers to build recipes.
* Check installed Ansible collections before starting **[netlab up](netlab-up)** or **[netlab initial](netlab-initial)**
* Support for [Sonic VM](platform-devices) based on Azure sonic-vs images.
* [Numerous improvements](release-1.8.2-vagrant) in the Vagrant box-building process

[More features...](release-1.8.2)

**Release 1.8.1-post1 (2024-04-24)**

This release contains only [bug fixes](bug-fixes-1.8.1-post1) and [documentation fixes](doc-fixes-1.8.1-post1).

**[Release 1.8.1](release-1.8.1) (2024-04-08)**

* Refactor the **[netlab status](netlab-status)** printout
* Add '[retry tests until the timeout](validate-retry)' functionality to **[netlab validate](netlab-validate)** (including the actual time it took to get the expected results).
* [OSPFv3 in VRFs](module-vrf-platform-routing-support), implemented on Arista EOS, Cisco IOS, Cisco IOS-XE, FRR, and Junos (vMX, vPTX, vSRX).
* [EBGP sessions over IPv4 unnumbered and IPv6 LLA interfaces](bgp-platform) on Arista EOS
* Cisco IOS XRd container support
* [Numerous configuration template fixes](release-1.8.1-device-fixes), including reduced OSPF SPF/LSA and IPv6 ND RA timers.

[More features...](release-1.8.1)

**[Release 1.8.0](release-1.8.0) (2024-03-01)**

* **netlab up** command can [reload saved device configurations](netlab-up-reload) instead of starting the initial device configuration process.
* [DHCP configuration module](module-dhcp) implements DHCP clients, DHCP servers, and DHCP relays for IPv4 and IPv6.
* Lab topology can include control plane- and network services [daemons](platform-daemons) running in Linux containers. This release includes BIRD and dnsmasq daemons.
* [BGP configuration module](module-bgp) supports 4-octet BGP AS numbers and [large BGP communities](bgp-community-propagation).
* [Validation plugins](validate-plugin) allow you to write more powerful **netlab validate** validation tests without creating complex Jinja2 templates
* You can build Docker containers for the [supported daemons](platform-daemons) with the **[netlab clab build](netlab-clab-build)** command

[More features...](release-1.8.0)

**Release 1.7.2 (2024-01-26)**

This release contains only [bug fixes](bug-fixes-1.7.2) and [documentation fixes](doc-fixes-1.7.2).

**[Release 1.7.1](release-1.7.1) (2024-01-08)**

* [Automatically create nodes from group members](groups-auto-create)
* [Add 'wait' parameter](validate-wait) to validation tests
* Use colors in netlab up/down/test/validate printouts
* Use color-coded error messages
* Use the **rich** Python library to pretty-print tables, JSON, and YAML

[More features...](release-1.7.1)

**[Release 1.7.0](release-1.7.0) (2023-12-03)**

* **[netlab validate](netlab/validate.md)** command can be used to execute [lab validation tests](topology/validate.md).
* The [**fabric** plugin](plugins/fabric.md) generates a whole leaf-and-spine fabric topology from a few parameters.
* The [**bgp.domain** plugin](plugins/bgp.domain.md) allows you to create topologies with multiple independent devices or sites using the same BGP AS number.
* The [**bgp.policy** plugin](plugins/bgp.policy.md) supports AS-path prepending on Arista EOS, Aruba AOS-CX, Cisco CSR 1000v, Cisco IOSv, Cumulus Linux, FRR
* [**bgp.originate** plugin](plugins/bgp.originate.md) uses loopbacks (instead of static routes to Null device) to originate BGP IPv4 and IPv6 prefixes
* The `--show` option of the **[netlab connect](netlab/connect.md)** command implements a consistent cross-device way of executing show commands.

[More features...](release-1.7.0)

**[Release 1.6.4](release-1.6.4) (2023-10-23)**

* Implement simple BGP routing policies in [bgp.policy plugin](plugins/bgp.policy.md)
* Implement **[remove_private_as](bgp-session-as-path)**, passive BGP peers and [BFD for BGP neighbors](bgp-session-platforms) in [bgp.session plugin](plugins/bgp.session)
* [Selectively apply BGP session attributes](bgp-session-apply) to IBGP and EBGP sessions
* [Enable external tools](tools-enable-default) in user defaults
* [Default groups](default-groups) allow you to specify user- or project-wide groups in the defaults files.

{.text-right}
[More features...](release-1.6.4)

**[Release 1.6.3](release-1.6.3) (2023-10-06)**

* [EBGP multihop sessions](plugins/ebgp.multihop.md)
* [ebgp.utils plugin](plugins/ebgp.utils.md) supports TCP-AO, configurable BGP timers, and Generic TTL Security Mechanism (TTL session protection)
* [OSPF reports](module/ospf.md)
* Shorter version of [BGP neighbor report](module/bgp.md)
* [BFD on Cumulus Linux](bfd-platform)

{.text-right}
[More features...](release-1.6.3)

**[Release 1.6.2](release-1.6.2) (2023-08-26)**

* [Support for ArubaOS-CX with containerlab](platforms.md#supported-virtual-network-devices)
* Display a subset of available reports in **[netlab show reports](netlab-show-reports)** command
* Display warnings in reports relying on **ipaddr** Ansible filter
* Add IPv6 prefixes and neighbors to BGP reports
* Add IPv6 column to text addressing report
* Make some report columns optional to reduce the report width
* Implement [inter-VRF route leaking](module/vrf.md#platform-support) for Cumulus/FRR

**[Release 1.6.1](release-1.6.1) (2023-08-18)**

* **[netlab report](netlab/report.md)** can generate Markdown markup (ideal for augmenting documentation written in Markdown)
* BGP AS number and BGP neighbor reports (text, Markdown, HTML)
* [Make user/system default locations configurable](defaults-locations)

**[Release 1.6.0](release-1.6.0) (2023-08-01)**

* New commands: **[netlab report](netlab/report.md)**, **[netlab graph](netlab/graph.md)** and **[netlab inspect](netlab/inspect.md)**
* New reports: node and link addressing, lab wiring, management IP addresses and credentials
* Improved **[netlab show](netlab/show.md)** command can display [configuration modules](modules.md), [output modules](outputs/index.md), [virtualization providers](providers.md) and reports
* [Connect containers to outside world](clab-network-external) through *macvlan* interfaces
* Host-to-lab-device port forwarding with [*libvirt*](libvirt-port-forwarding) and *[containerlab](clab-port-forwarding)*
* Nokia SR OS OSPF P2MP support

{.text-right}
[More features...](release-1.6.0)

**[Release 1.5.4](release-1.5.4) (2023-06-10)**

* [Juniper vPTX/vEVO](platforms.md) support by Stefano Sasso (initial configuration, IPv4+IPv6, OSPFv2/v3, IS-IS, BGP, BFD, VLANs, VRFs, MPLS, SR-MPLS)
* [Juniper vSRX](platforms.md) can be run as a *vrnetlab*-packaged container (by Stefano Sasso)
* Documentation migrated to [netlab.tools](https://netlab.tools)

**[Release 1.5.3](release-1.5.3) (2023-05-15)**

* ['unknown' device type](platform-unknown) can be used to deploy devices not yet supported by *netlab*
* [Public *libvirt* networks](libvirt-network-external) can be used to connect labs to outside world
* MPLS VPN support for SR OS
* Improved virtualization provider installation testing with (hopefully) useful error messages

{.text-right}
[More features...](release-1.5.3)

**[Release 1.5.2](release-1.5.2) (2023-04-27)**

* [External network management tools](extools.md)
* [Aruba AOS-CX Support](platforms.md)
* [Reusable topology components](components.md)
* [Tunnel interfaces](links-tunnel)
* Add `--force flag to '[netlab down](netlab/down.md)' command
* Use [Ansible filters in netlab templating system](labs/clab.md#jinja2-filters-available-in-custom-configuration-files)
* Deploy [per-node custom configuration templates](dev/config/deploy.md#finding-custom-configuration-templates)

**[Release 1.5.1](release-1.5.1) (2023-04-02)**

* [Simplified definition of VLAN access links](module-vlan-creating-access-links)
* [Simplified definition of VRF links](module-vrf-links)
* [Link groups](link-groups)
* Stricter type checks for node names, group names, VLAN names, VRF names, link roles, address pools, device names, and Linux bridges. Names must be *identifiers*: alphanumeric strings up to 16 characters long.
* *netlab* status file [tracks active lab instances](netlab/status.md) -- used by **[netlab create](netlab/create.md)**, **[netlab up](netlab/up.md)** and **[netlab down](netlab/down.md)** commands to check for duplicate lab instances.
* [Output module](outputs/d2.md) for [D2 diagram scripting language](https://d2lang.com/tour/intro)

**[Release 1.5.0](release-1.5.0) (2023-01-28)**

* [Multi-provider topologies](labs/multi-provider.md)
* [Running multiple lab instances on Linux Servers](plugins/multilab.md)
* Split large *libvirt* topology into [smaller **vagrant up** batches](labs/libvirt.md#starting-virtual-machines-in-batches)
* [Use custom network/bridge name and IP subnet](labs/libvirt.md#libvirt-management-network) for `vagrant-libvirt` management network
* ['loopback' link type](links.md#loopback-links) can be used to create additional loopback interfaces

{.text-right}
[More features...](release-1.5.0)

**[Release 1.4.3](release-1.4.3) (2023-01-12)**

* [IOS XRv](platforms.md) support (initial configuration, IPv4+IPv6, OSPFv2/v3, IS-IS, BGP)
* [MPLS, LDP and L3VPN](module/mpls.md) support on FRR
* [Rewrite Linux container deployment](clab-linux) to remove Python and `ip` dependencies
* [Custom templates for container configuration files](clab-config-template)

**[Release 1.4.2](release-1.4.2) (2022-12-18)**

* [Juniper vMX](platforms.md) support
* Junos BFD, VRF, MPLS, SR-MPLS, and MPLS/VPN support
* Full VLAN support on vMX and routed VLAN interfaces on vSRX
* CSR 1000v VLAN and VXLAN support
* VyOS containerlab support

**[Release 1.4.1](release-1.4.1) (2022-11-25)**

* Cisco ASAv support
* VRRP and anycast gateway on Dell OS10
* VRRP on VyOS
* Unnumbered OSPF interfaces on VyOS
* Add support for all EVPN bundle services

**[Release 1.4.0](release-1.4.0) (2022-11-04)**

* EVPN asymmetric IRB
* Anycast gateway and VRRP
* EVPN MPLS transport
* New address allocation algorithm for links with small IPv4 prefixes
* Tighter control of VXLAN-enabled and EVPN-controlled VLANs and VRFs
* Unmanaged and unprovisioned devices

For older releases, check the [release notes archive](release-archive.md).

```eval_rst
.. toctree::
   :caption: Individual release notes
   :maxdepth: 2

   release/1.8.md
   release/1.7.md
   release/1.6.md
   release/1.5.md
   release/1.4.md
   release-archive.md
```   
