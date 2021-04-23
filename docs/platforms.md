# Supported Platforms

The following virtual network devices are supported by **config-generate** (use the device type in brackets):

* Cisco IOSv (iosv)
* Cisco CSR1000v (csr)
* Cisco Nexus 9300v (nxos)
* Arista vEOS (eos)
* Arrcus ArcOS (arcos)
* Juniper vSRX 3.0 (vsrx)

## Supported Network Operating Systems

Network operating systems supported by **config.ansible** and **collect-configs.ansible**:

* Cisco IOS
* Cisco IOS XE
* Cisco Nexus OS
* Arista EOS
* Arrcus ArcOS
* Junos

## Supported Initial Device Configurations

Network operating systems supported by **initial-config.ansible**:

* Cisco IOS (IOSv)
* Cisco IOS XE (CSR 1000v)
* Cisco Nexus OS (Nexus 9300v)
* Arista EOS (vEOS)
* Arrcus ArcOS
* Junos (vSRX 3.0)

## Supported Configuration Modules

* OSPF configuration module is available for all supported devices.
* BGP and IS-IS configuration modules are available for Cisco IOS, Cisco Nexus OS, Arista EOS and Junos.
* SR-MPLS configuration module is available for Cisco IOS XE and Arista EOS.

## Supported Virtualization Providers

Virtualization providers supported by **config-generate**:

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/) (added in release 0.5)

Details of VirtualBox and Containerlab support are described below, for extensive vagrant-libvirt details please [refer to the installation guide](install.html#building-a-libvirt-based-lab).

### Vagrant with VirtualBox

* Most networking vendors don't ship Vagrant boxes, and I had no interest in building VirtualBox boxes from scratch after setting up a *libvirt*-based lab on an Intel NUC. The only boxes I could get with zero hassle were Cisco Nexus 9300v and Arista vEOS, and they both work fine. If you want to add other devices, you'll have to modify *topology-defaults.yml* file.
* The latest version of Arista vEOS available as Vagrant box for VirtualBox is 4.21.14M.
* Vagrantfile created by **create-topology** sets up port forwarding for SSH (22), HTTP (80) and NETCONF (830), but the corresponding Ansible inventory contains only **ansible_port** (SSH). You could edit the final inventory by hand, add extra file to `host_vars`, or fix my code. Should you decide to do the latter, please contact me in advance to discuss the necessary data structures.

### Containerlab

* The only device currently supported is Arista cEOS
* Feel free to extend the templates and defaults to support other network devices
