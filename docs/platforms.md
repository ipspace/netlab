# Supported Platforms

The following virtual network devices are supported by *netsim-tools*:

| Virtual network device | netsim device type |
|------------------------|--------------------|
| Arista vEOS            | eos                |
| Arrcus ArcOS           | arcos              |
| Cisco IOSv             | iosv               |
| Cisco CRS 1000v        | csr                |
| Cisco Nexus 9300v      | nxos               |
| Cumulus Linux          | cumulus            |
| FRR 7.5.0              | frr                |
| Juniper vSRX 3.0       | vsrx               |
| Nokia SR Linux         | srlinux            |

**Notes:**
* **netsim-tools** support FRR containers with **containerlab**. It seems that the FRR build tools changed the file system layout after release 7.5.0, crashing **containerlab** deployment process.

To specify the device type of a node in your virtual lab:

* Specify **device** property in node data

```
nodes:
- name: c_ios
  device: iosv
- name: c_csr
  device: csr
```

* Use **defaults.device** setting in lab topology

```
defaults:
  device: cumulus

nodes: [ s1, s2, s3 ]
```

## Supported Virtualization Providers

**netlab create** can generate configuration files for these virtualization providers:

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/)

You cannot use all supported network devices with all virtualization providers:

| Virtual network device | Vagrant<br />Libvirt | Vagrant<br />Virtualbox | Containerlab |
|------------------------|:-:|:-:|:-:|
| Arista vEOS            | ✅ | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ❌ | ❌ |
| Cisco IOSv             | ✅ | ❌ | ❌ |
| Cisco CRS 1000v        | ✅ | ❌ | ❌ |
| Cisco Nexus 9300v      | ✅ | ✅ | ❌ |
| Cumulus Linux          | ✅ | ✅ | ✅ |
| FRR 7.5.0              | ❌ | ❌ | ✅ |
| Juniper vSRX 3.0       | ✅ | ❌ | ❌ |
| Nokia SR Linux         | ❌ | ❌ | ✅ |

**Implementation Caveats**
* *containerlab* could run Cumulus Linux as a container or as a micro-VM with *firecracker* (default, requires KVM). To run Cumulus VX as a pure container, add **runtime: docker** parameter to node data.
* Release 0.8.1 uses Cumulus VX containers created by Michael Kashin and downloaded from his Docker Hub account. Once Nvidia releases an official container image, change the container name with **defaults.providers.clab.devices.cumulus.image.clab** parameter (or by editing the `topology-defaults.yml` file included with *netsim-tools*).

**Notes on Extending Device- or Virtualization Provider Support**

* It's possible to run Cisco IOSv/CSR or Juniper vSRX under Virtualbox if you build your own Vagrant boxes.
* After building Vagrant boxes, edit **devices** section of **topology-defaults.yml** file to add Virtualbox support for individual network devices.
* If you feel like building a downloadable Vagrant box for FRR, please send us the box name and we'll add it to **topology-defaults.yml** file.

## Configuration Deployments

Ansible playbooks included with **netsim-tools** can deploy and collect device configuration on these network operating systems:

| Operating system | Deploy configuration | Collect configuration |
|------------------------|:-:|:-:|
| Arista EOS             | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ✅ |
| Cisco IOS / IOS XE     | ✅ | ✅ |
| Cisco Nexus OS         | ✅ | ✅ |
| Cumulus Linux          | ✅ | ✅ |
| FRR container          | ✅ | ❌ |
| Juniper vSRX 3.0       | ✅ | ✅ |
| Nokia SR Linux         | ❌ | ❌ |

## Initial Device Configurations

The following system-wide features are configured on supported network operating systems as part of initial device configuration:

| Operating system | Hostname | IPv4 hosts | LLDP | Loopback<br />IPv4 address|Loopback<br />IPv6 address |
|------------------------|:-:|:-:|:-:|:-:|:-:|
| Arista EOS             | ✅ | ✅ | ✅ | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ❌ | ✅ | ✅ | ✅ |
| Cisco IOS/IOS XE       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco Nexus OS         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux          | ✅ | ✅ | ✅ | ✅ | ✅ |
| FRR 7.5.0              | ✅ | ❌ | ❌ | ✅ | ✅ |
| Juniper vSRX 3.0       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux         | ❌ | ❌ | ❌ | ❌ | ❌ |

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />interfaces | Interface<br />description | Interface<br />bandwidth |
|------------------------|:-:|:-:|:-:|:-:|:-:|
| Arista EOS             | ✅ | ✅ | ✅ | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cisco IOS/IOS XE       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco Nexus OS         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux          | ✅ | ✅ | ✅ | ✅ | ✅ |
| FRR 7.5.0              | ✅ | ✅ | ❌ | ✅ | ✅ |
| Juniper vSRX 3.0       | ✅ | ✅ | ✅ | ✅ | ✅ |

## Supported Configuration Modules

Individual **netsim-tools** [configuration modules](module-reference.md) are supported on these devices:

| Operating system | OSPF | IS-IS | EIGRP | BGP | SR-MPLS |
|------------------------|:-:|:-:|:-:|:-:|:-:|
| Arista EOS             | ✅ | ✅ | ❌ | ✅ | ✅ 
| Arrcus ArcOS           | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cisco IOS              | ✅ | ✅ | ✅ | ✅ | ❌ |
| Cisco IOS XE           | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco Nexus OS         | ✅ | ✅ | ✅ | ✅ | ❌ |
| Cumulus Linux          | ✅ | ❌ | ❌ | ✅ |  ❌ |
| FRR 7.5.0              | ✅ | ✅ | ❌ | ✅ | ❌ |
| Juniper vSRX 3.0       | ✅ | ✅ | ❌ | ✅ | ❌ |
| Nokia SR Linux         | ❌ | ❌ | ❌ | ❌ | ❌ |

## IPv6 Support

Core functionality of *netsim-tools* and all multi-protocol routing protocol configuration modules fully supports IPv6. OSPFv3 is not implemented yet.

| Operating system | IPv6<br />addresses | OSPFv3 | IS-IS MT | EIGRP<br />IPv6 AF | BGP<br />IPv6 AF | SR-MPLS |
|------------------------|:-:|:-:|:-:|:-:|:-:|:-:|
| Arista EOS             | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Cisco IOS              | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Cisco IOS XE           | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Cisco Nexus OS         | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Cumulus Linux          | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| FRR 7.5.0              | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| Juniper vSRX 3.0       | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |

<!--
## BGP Support

Some BGP parameters are not supported on all devices:

| Operating system | IPv6 address<br />family |
|------------------------|:-:|
| Arista EOS             | ❌ |
| Cisco IOS/IOS XE       | ❌ |
| Cisco Nexus OS         | ❌ |
| Cumulus Linux          | ❌ |
| FRR 7.5.0              | ❌ |
| Juniper vSRX 3.0       | ❌ |
-->