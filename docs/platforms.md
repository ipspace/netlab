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
| Generic Linux host     | linux              |
| Juniper vSRX 3.0       | vsrx               |
| Nokia SR Linux         | srlinux            |
| VyOS                   | vyos               |

**Notes:**

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

See [lab topology overview](topology-overview.md) for more details.

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
| Generic Linux (Ubuntu/Alpine) | ✅ | ✅ | ✅ | 
| Juniper vSRX 3.0       | ✅ | ❌ | ❌ |
| Nokia SR Linux         | ❌ | ❌ | ✅ |
| VyOS                   | ✅ | ❌ | ❌ |

**Implementation Caveats**

* *containerlab* could run Cumulus Linux as a container or as a micro-VM with *firecracker* (default, requires KVM). To run Cumulus VX as a pure container, add **runtime: docker** parameter to node data.
* *netsim-tools* uses Cumulus VX containers created by Michael Kashin and downloaded from his Docker Hub account. Once Nvidia releases an official container image, change the container name with **defaults.providers.clab.devices.cumulus.image.clab** parameter (or by editing the `topology-defaults.yml` file included with *netsim-tools*).
* *containerlab* FRR containers run FRR release 7.5.0 -- the latest release that survives FRR daemon restart during the initial configuration process.
* FRR project does not create usable Ubuntu packages. Use Cumulus Linux if you'd like to run FRR within a VM.
* *Generic Linux device* is a Linux VM running Ubuntu 20.04 or an Alpine/Python container. To use any other Linux distribution, add **image** attribute with the name of Vagrant box or Docker container to the node data[^1]; the only requirements are working Python environment (to support Ansible playbooks used in **netlab initial** command) and the presence of **ip** command used in initial device configuration. See also [host routing](#host-routing).

[^1]: You can also set the **defaults.devices.linux.image._provider_** attribute to change the Vagrant box for all Linux hosts in your lab.

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
| Generic Linux          | ✅ | ❌ |
| Juniper vSRX 3.0       | ✅ | ✅ |
| Nokia SR Linux         | ❌ | ❌ |
| VyOS                   | ✅ | ✅ |

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
| Generic Linux          | ✅ | ✅ | ✅ | ✅ | ✅ |
| Juniper vSRX 3.0       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux         | ❌ | ❌ | ❌ | ❌ | ❌ |
| VyOS                   | ✅ | ✅ | ✅ | ✅ | ✅ |

**Caveats:**

* LLDP on Generic Linux is started in Ubuntu VMs but not in Alpine containers.

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />interfaces | Interface<br />description | Interface<br />bandwidth |
|------------------------|:-:|:-:|:-:|:-:|:-:|
| Arista EOS             | ✅ | ✅ | ✅ | ✅ | ✅ |
| Arrcus ArcOS           | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cisco IOS/IOS XE       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco Nexus OS         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux          | ✅ | ✅ | ✅ | ✅ | ✅ |
| FRR 7.5.0              | ✅ | ✅ | ❌ | ✅ | ✅ |
| Generic Linux          | ✅ | ✅ | ❌ | ❌  | ❌ |
| Juniper vSRX 3.0       | ✅ | ✅ | ✅ | ✅ | ✅ |
| VyOS                   | ✅ | ✅ | ❌ | ✅ | ❌ |

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
| Generic Linux          | ❌ | ❌ | ❌ | ❌ | ❌ |
| Juniper vSRX 3.0       | ✅ | ✅ | ❌ | ✅ | ❌ |
| Nokia SR Linux         | ❌ | ❌ | ❌ | ❌ | ❌ |
| VyOS                   | ✅ | ❌ | ❌ | ✅ | ❌ |

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
| Generic Linux          | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Juniper vSRX 3.0       | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| VyOS                   | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |

## Host Routing

Generic Linux device is an IP host that does not support IP forwarding or IP routing protocols. It uses static routes set up as follows:

* IPv4 default route points to Vagrant management interface (set by Vagrant/DHCP).
* IPv6 default route points to whichever adjacent device is sending IPv6 Route Advertisement messages (default Linux behavior).
* IPv4 static routes for all IPv4 address pools defined in lab topology point to the first neighbor on the first non-management interface.

**Corollary:** Linux devices SHOULD have a single P2P link to an adjacent network device. If you encounter problems using any other lab topology, please submit a Pull Request fixing it instead of complaining ;)

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