# Tutorials

We published dozens of tutorials describing various _netlab_ features. Choose one of these to get started:

* [Build a simple network with two routers](tutorial-github)
* [Run BGP labs in GitHub Codespaces](https://blog.ipspace.net/2024/06/bgp-labs-github-codespaces/)
* [Run netlab on Apple silicon](https://blog.ipspace.net/2024/03/netlab-bgp-apple-silicon/) (also applicable to other platforms)
* [Run netlab examples in GitHub Codespaces](https://blog.ipspace.net/2024/07/netlab-examples-codespaces/)

These instructions and tutorials cover some of the usual early hurdles:

* [Building Vagrant boxes](libvirt-build-boxes)
* [Building or installing containers](clab-images)
* [Selecting Network Devices' Software Release](tutorial-release)
* [](tutorial-linux)

```eval_rst
.. contents:: Other Tutorials
   :depth: 1
   :local:
```

## Lab Topology Tutorials

Once you want to know more, check out these lab topology tutorials:

* [Link definitions](example/link-definition.md)
* [Addressing](example/addressing-tutorial.md)
* [netlab Custom Groups and Deployment Templates](https://blog.ipspace.net/2021/11/netsim-groups-deployment-templates/)
* [Simplify netlab Topologies with Link Groups](https://blog.ipspace.net/2023/05/netlab-link-groups/)
* [Mix Containers and VMs in the Same Lab Topology](https://blog.ipspace.net/2023/02/netlab-vm-containers/)
* [Using VLAN and VRF Links](https://blog.ipspace.net/2023/04/netlab-vrf-vlan-links/)

## User Interface Tutorials

Want to draw graphs, create reports, or use the GUI?

* [Network Topology Graphs](https://blog.ipspace.net/2021/09/netsim-tools-graphs.html)
* [Using Graphite as netlab GUI](https://blog.ipspace.net/2022/04/netsim-tools-better-with-gui/)
* [Using netlab Reports](https://blog.ipspace.net/2024/07/using-netlab-reports/)

## VRFs, VLANs, VXLAN, and EVPN

VRFs and VLANs are particularly tricky, so we created numerous examples for simple- and complex topologies using them:

* [Simple VLAN Example](https://blog.ipspace.net/2022/05/netsim-vlan-simple/)
* [VLAN Trunk Example](https://blog.ipspace.net/2022/06/netsim-vlan-trunk/)
* [Combining VLANs with VRFs](https://blog.ipspace.net/2022/06/netsim-vlan-vrf/)
* [Creating VRF Lite Labs With netlab](https://blog.ipspace.net/2022/04/netsim-vrf-lite/)
* [VRF Lite Topology with VLAN Trunks](https://blog.ipspace.net/2022/09/netlab-vrf-lite/)
* [Creating MPLS/VPN Labs With netlab](https://blog.ipspace.net/2022/04/netsim-mpls-vpn/)
* [Router-on-a-Stick Example](https://blog.ipspace.net/2022/10/netlab-router-stick/)
* [IRB with Anycast Gateways](https://blog.ipspace.net/2022/11/netlab-anycast-gateway/)
* [Building a Layer-2 Fabric](https://blog.ipspace.net/2023/01/netlab-l2-fabric/)

There are also examples describing EVPN and VXLAN features:

* [Simple VXLAN Bridging](https://blog.ipspace.net/2022/09/netlab-vxlan-bridging/)
* [VXLAN Leaf-and-Spine Fabric](https://blog.ipspace.net/2024/04/evpn-designs-vxlan-leaf-spine-fabric/)
* [EVPN/VXLAN Bridging Example](https://blog.ipspace.net/2022/10/netlab-evpn-vxlan-bridging/)
* [IBGP Full Mesh Between Leaf Switches](https://blog.ipspace.net/2024/05/evpn-designs-ibgp-full-mesh/)
* [VXLAN Router-on-a-Stick Example](https://blog.ipspace.net/2022/11/netlab-vxlan-router-stick/)
* [VRF Lite over VXLAN Transport](https://blog.ipspace.net/2022/12/netlab-vxlan-vrf-lite/)
* [Building Layer-3-Only EVPN Lab](https://blog.ipspace.net/2024/08/netlab-layer-3-only-evpn/)

## Even More Examples

More practical examples:

* [Creating BGP Multipath Lab with netlab](https://blog.ipspace.net/2021/11/bgp-multipath-netsim-tools.html) (lab topology using BGP and OSPF)
* [Building Unnumbered Ethernet Lab with netlab](https://blog.ipspace.net/2021/04/build-unnumbered-lab-netsim-tools.html) (using unnumbered interfaces)
* [Anycast Works Just Fine with MPLS/LDP](https://blog.ipspace.net/2021/11/anycast-mpls.html) (custom configuration templates)
* [Optimal BGP Path Selection with BGP Additional Paths](https://blog.ipspace.net/2021/12/bgp-multipath-addpath.html) (custom deployment templates)
* [Building a BGP Anycast Lab](https://blog.ipspace.net/2021/12/bgp-anycast-lab.html) (group-wide node data, auto-generated groups)

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
   example/linux.md
```
