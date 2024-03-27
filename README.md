# Overview

*[netlab](https://netlab.tools)* is bringing infrastructure-as-code concepts to networking labs. You'll describe your high-level network topology and routing design in a YAML file, and the tools in this repository will

* Create *Vagrantfile* configuration file for *VirtualBox* or *libvirt* environment
* Create *containerlab* configuration file
* Create Ansible inventory and configuration file
* Create IPv4 and IPv6 addressing plan and OSPFv2, OSPFv3, EIGRP, IS-IS, and BGP routing design
* Configure IPv4, IPv6, DHCP, DHCPv6, VLANs, VRFs, VXLAN, LLDP, BFD, OSPFv2, OSPFv3, EIGRP, IS-IS, BGP, VRRP, anycast gateways, MPLS, BGP-LU, L3VPN (VPNv4 + VPNv6), 6PE, EVPN, SR-MPLS, or SRv6 on your lab devices.

Instead of wasting time creating lab topology in a GUI and configuring boring details, you'll start with a lab preconfigured according to your specifications.

Interested? [Read the documentation](https://netlab.tools) and [installation guidelines](https://netlab.tools/install/).

## Releases

The latest release is [release 1.8.0](https://github.com/ipspace/netlab/releases/tag/release_1.8.0). It contains [numerous new features](https://netlab.tools/release/1.8/) that might have a few bugs. Should you encounter one of those creatures, please report it with [a GitHub issue](https://github.com/ipspace/netlab/issues/new/choose) and use [release 1.7.2](https://github.com/ipspace/netlab/releases/tag/release_1.7.2).

<!--
If you encounter bugs using release 1.7.x, please downgrade to [1.6.4](https://github.com/ipspace/netlab/releases/tag/release_1.6.4) and [open a GitHub issue](https://github.com/ipspace/netlab/issues).
-->

## An Overview of CLI Commands

**netlab up**
: Uses **[netlab create](https://netlab.tools/netlab/create/)** to create configuration files, starts the virtual lab, and uses **[netlab initial](https://netlab.tools/netlab/initial/)** to deploy device configurations, including IP addressing, LLDP, OSPF, BGP, IS-IS, EIGRP, VRRP, VLANs, VRFs, MPLS, SR-MPLS, VXLAN, EVPN and SRv6. [More details](https://netlab.tools/netlab/up/)

**netlab down**
: Destroys the virtual lab. [More details](https://netlab.tools/netlab/down/)

**netlab restart**
: Restart and/or reconfigure the virtual lab. [More details](https://netlab.tools/netlab/restart/)

**netlab config**
: Applies additional Jinja2 configuration templates to network devices.

**netlab collect**
: Using Ansible fact gathering or other device-specific Ansible modules, collects device configurations and saves them in the specified directory (default: **config**).

**netlab connect**
: Use SSH or **docker exec** to [connect to a lab device](https://netlab.tools/netlab/connect/) using device names, management network IP addresses (**ansible_host**), SSH port, and username/passwords specified in lab topology or *netlab* device defaults.

**netlab report**
: Creates a report from the transformed lab topology data.  [More details](https://netlab.tools/netlab/report/)

**netlab graph**
: Creates a lab topology graph description in Graphviz or D2 format. [More details](https://netlab.tools/netlab/graph/)

**netlab show**
: Display system settings in tabular, text, or YAML format. [More details](https://netlab.tools/netlab/show/)
