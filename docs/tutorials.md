# Tutorials

We published dozens of tutorials describing various _netlab_ features. Choose one of these to get started:

* [Build a simple network with two routers](tutorial-github)
* [Run BGP labs in GitHub Codespaces](https://blog.ipspace.net/2024/06/bgp-labs-github-codespaces/)
* [Run netlab on Apple silicon](https://blog.ipspace.net/2024/03/netlab-bgp-apple-silicon/) (also applicable to other platforms)
* [Run netlab examples in GitHub Codespaces](https://blog.ipspace.net/2024/07/netlab-examples-codespaces/)

These instructions and tutorials cover some of the usual early hurdles:

* [Building or installing containers](clab-images)
* [Building Vagrant boxes](libvirt-build-boxes)
* [Selecting Network Devices' Software Release](tutorial-release)
* [](tutorial-linux)

```eval_rst
.. contents:: Other Tutorials
   :depth: 1
   :local:
```

## Installation Tutorials

Not sure how to get started? These tutorials walk you through the _netlab_ installation:

* [Labs as Code (Part 1): Install netlab, Build a Lab in Five Minutes](https://routerjockey.com/labs-as-code-part-1/) by Tony Mattke
* [Netlab: The Fastest Way to Build Network Labs](https://www.packetswitch.co.uk/netlab-the-fastest-way-to-build-network-labs/) by Suresh Vina (from the very basics to a multi-vendor MPLS network)
* [Network Labs on a Budget](https://www.packetswitch.co.uk/network-labs-on-a-budget/) by Suresh Vinasiththamby (building a lab on a mini-PC)
* [Codespaces for Network Engineers and Educators](https://juliopdx.com/2024/11/25/codespaces-for-network-engineers-and-educators/) by Julio Perez (running _netlab_ in GitHub Codespaces)
* [Network Simulation Tools and containerlab](https://juliopdx.com/2022/02/13/network-simulation-tools-and-containerlab/) by Julio Perez (using _netlab_ with containerlab and Arista cEOS)

## Introductions to netlab

Articles, videos, and presentations explaining what _netlab_ is and how you can use it:

* [Getting Started with netlab](https://my.ipspace.net/bin/list?id=NetTools#NETLAB) videos
* [What is Netlab and Why Network Engineers Should Care](https://netodata.io/what-is-netlab-and-why-network-engineers-should-care/) by Milan Zapletal
* [Lab as Code (containerlab and netlab)](https://theworldsgonemad.net/2025/lab-as-code-pt2/) by @sjhloco
* [Let's IaC Some Network Labs](https://www.linkedin.com/pulse/lets-iac-some-network-labs-roman-pomazanov-tu1pe/) by Roman Pomazanov (comparing GNS3, containerlab, and _netlab_)
* [Netlab – Automate Your Network Labs With YAML!](https://www.youtube.com/watch?v=ExPh5jBfKR0) by Ethan Banks (video)
* [Getting Started with netlab](https://www.youtube.com/watch?v=yR5xr7UuJpw) (Cisco DevNet interview with Suresh Vina)

## Lab Topology Tutorials

Once you want to know more, check out these lab topology tutorials:

* [](link-example)
* [](addressing-example)
* [netlab Custom Groups and Deployment Templates](https://blog.ipspace.net/2021/11/netsim-groups-deployment-templates/)
* [Simplify netlab Topologies with Link Groups](https://blog.ipspace.net/2023/05/netlab-link-groups/)
* [netlab Topology File](https://blog.ipspace.net/2023/04/video-netlab-topology-file/) (video)
* [netlab IP Address Management (IPAM)](https://blog.ipspace.net/2023/12/video-netlab-ipam/) (video)
* [Mix Containers and VMs in the Same Lab Topology](https://blog.ipspace.net/2023/02/netlab-vm-containers/)
* [Using VLAN and VRF Links](https://blog.ipspace.net/2023/04/netlab-vrf-vlan-links/)
* [](example-bridge)
* [](node-debug)

## User Interface Tutorials

Want to draw graphs, create reports, or use the GUI?

* [Network Topology Graphs](https://blog.ipspace.net/2021/09/netsim-tools-graphs.html)
* [Using Graphite as netlab GUI](https://blog.ipspace.net/2022/04/netsim-tools-better-with-gui/)
* [Using netlab Reports](https://blog.ipspace.net/2024/07/using-netlab-reports/)

(tutorials-vlan-vrf)=
## VRFs and VLANs

VRFs and VLANs are particularly tricky, so we created numerous examples describing how you can use VLANs and VRFs with _netlab_. Here are a few basic examples:

* [Simple VLAN Example](https://blog.ipspace.net/2022/05/netsim-vlan-simple/)
* [VLAN Trunk Example](https://blog.ipspace.net/2022/06/netsim-vlan-trunk/)
* [Combining VLANs with VRFs](https://blog.ipspace.net/2022/06/netsim-vlan-vrf/)
* [](example-vlan-addressing)
* [](example-vlan-mode)

More complex examples:

* [Creating VRF Lite Labs With netlab](https://blog.ipspace.net/2022/04/netsim-vrf-lite/)
* [VRF Lite Topology with VLAN Trunks](https://blog.ipspace.net/2022/09/netlab-vrf-lite/)
* [Creating MPLS/VPN Labs With netlab](https://blog.ipspace.net/2022/04/netsim-mpls-vpn/)
* [Router-on-a-Stick Example](https://blog.ipspace.net/2022/10/netlab-router-stick/)
* [IRB with Anycast Gateways](https://blog.ipspace.net/2022/11/netlab-anycast-gateway/)
* [Building a Layer-2 Fabric](https://blog.ipspace.net/2023/01/netlab-l2-fabric/)

(tutorials-vxlan-evpn)=
## VXLAN and EVPN

These examples describe VXLAN and EVPN features:

* [Simple VXLAN Bridging](https://blog.ipspace.net/2022/09/netlab-vxlan-bridging/)
* [VXLAN Leaf-and-Spine Fabric](https://blog.ipspace.net/2024/04/evpn-designs-vxlan-leaf-spine-fabric/)
* [EVPN/VXLAN Bridging Example](https://blog.ipspace.net/2022/10/netlab-evpn-vxlan-bridging/)
* [IBGP Full Mesh Between Leaf Switches](https://blog.ipspace.net/2024/05/evpn-designs-ibgp-full-mesh/)
* [VXLAN Router-on-a-Stick Example](https://blog.ipspace.net/2022/11/netlab-vxlan-router-stick/)

Looking for advanced examples? How about:

* [VRF Lite over VXLAN Transport](https://blog.ipspace.net/2022/12/netlab-vxlan-vrf-lite/)
* [Building Layer-3-Only EVPN Lab](https://blog.ipspace.net/2024/08/netlab-layer-3-only-evpn/)
* [Common Services VRF with EVPN Control Plane](https://blog.ipspace.net/2024/08/evpn-common-services-vrf/)
* [EVPN Hub-and-Spoke Layer-3 VPN](https://blog.ipspace.net/2024/09/hub-spoke-evpn/)
* [Building VXLAN/EVPN Data Center Lab with netlab](https://blog.ipspace.net/2025/11/worth-reading-netlab-vxlan-evpn/) (Dmitry Klepcha's lab series, from a simple IP network to symmetric IRB with MLAG)

## Segment Routing

These blog posts describe increasingly complex [SR-MPLS topologies](https://github.com/ipspace/sr-workshop):

* [Basic IS-IS Setup](https://blog.ipspace.net/2026/05/sr-mpls-intro/)
* [Dual-Stack SR-MPLS](https://blog.ipspace.net/2026/05/sr-mpls-dual-stack/)
* [SR-MPLS over Unnumbered Interfaces](https://blog.ipspace.net/2026/06/sr-mpls-unnumbered/)
* [SR-MPLS with OSPFv2](https://blog.ipspace.net/2026/06/sr-mpls-ospf/)
* [Multivendor SR-MPLS](https://blog.ipspace.net/2026/08/sr-mpls-multivendor/)
* [BGP-Free Core with SR-MPLS](https://blog.ipspace.net/2026/09/sr-mpls-bgp-free/)
* [MPLS/VPN with SR-MPLS Core](https://blog.ipspace.net/2026/09/sr-mpls-vpn/)
* [EVPN with SR-MPLS Core](https://blog.ipspace.net/2026/09/sr-mpls-evpn/)

(tutorials-use-cases)=
## Some Use Cases

* [CCIE Preparation with netlab](https://blog.ipspace.net/2024/07/netlab-ccie-preparation/)
* [Explore Configurations of Unfamiliar Devices with netlab](https://blog.ipspace.net/2026/02/netlab-device-configs/)
* [netlab as the Universal Configuration Translator](https://blog.ipspace.net/2025/12/netlab-configuration-translator/)
* [Vibe Coding netlab Lab Topology with ChatGPT](https://blog.ipspace.net/2025/05/chatgpt-netlab-topology/)
* [netlab Overview and Use Cases](https://blog.ipspace.net/2026/03/netlab-use-cases/) (NetBCN presentation, March 2026)
* [Introduction to netlab](https://blog.ipspace.net/2024/04/netlab-state-april-2024/) (RIPE SEE presentation, April 2024)
* [Labbing Network Technology Details with netlab](https://blog.ipspace.net/2025/09/labbing-network-technology-details/) (Software Gone Wild podcast)

## Even More Examples

More practical examples:

* [Creating BGP Multipath Lab with netlab](https://blog.ipspace.net/2021/11/bgp-multipath-netsim-tools.html) (lab topology using BGP and OSPF)
* [Building Unnumbered Ethernet Lab with netlab](https://blog.ipspace.net/2021/04/build-unnumbered-lab-netsim-tools.html) (using unnumbered interfaces)
* [Anycast Works Just Fine with MPLS/LDP](https://blog.ipspace.net/2021/11/anycast-mpls.html) (custom configuration templates)
* [Optimal BGP Path Selection with BGP Additional Paths](https://blog.ipspace.net/2021/12/bgp-multipath-addpath.html) (custom deployment templates)
* [Building a BGP Anycast Lab](https://blog.ipspace.net/2021/12/bgp-anycast-lab.html) (group-wide node data, auto-generated groups)
* [Testing IP Multicast with netlab](https://blog.ipspace.net/2025/11/worth-reading-netlab-multicast/)
* [Test Real-Life Routing Scenario with netlab](https://blog.ipspace.net/2026/11/worth-reading-netlab-routing-scenario/)
* [BGP labs](https://bgplabs.net) (hands-on lab exercises built with _netlab_)
* [netlab examples repository](https://github.com/ipspace/netlab-examples)

[Even more tutorials...](https://blog.ipspace.net/tag/netlab.html)

## Configuration Module Examples

Documentation of individual configuration modules includes sample lab topology files:

* [OSPF example](module/ospf.md#example)
* [IS-IS example](module/isis.md#example)
* [Multiple BGP examples](module/bgp.md#more-examples)
* [Segment Routing example](module/sr-mpls.md#example)

```eval_rst
.. toctree::
   :caption: Tutorials
   :maxdepth: 1
   :hidden:

   example/github.md
   example/release.md
   example/link-definition.md
   example/linux.md
   example/bridge.md
   example/vlan-addressing.md
   example/selecting-vlan-mode.md
```
