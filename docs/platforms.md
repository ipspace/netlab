# Supported Platforms

Virtual network devices supported by **config-generate** (require `topology-defaults.yml` settings and Vagrantfile templates in `templates/vagrant/provider`):

* Cisco IOSv
* Cisco CSR1000v
* Cisco Nexus 9300v
* Arista vEOS
* Arrcus ArcOS
* Juniper vSRX 3.0

Network operating systems supported by **config.ansible** (require device-specific task list in `ansible/config`):

* Cisco IOS
* Cisco Nexus OS
* Arista EOS
* Arrcus ArcOS
* Junos

Network operating systems supported by **initial-config.ansible** (require **config.ansible** support and initial device configuration template in `templates/initial`):

* Cisco IOS (IOSv and CSR 1000v)
* Cisco Nexus OS (Nexus 9300v)
* Arista EOS (vEOS)
* Arrcus ArcOS
* Junos (vSRX 3.0)

Virtualization providers supported by **config-generate**:

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/) (added in release 0.5)

Details of VirtualBox and Containerlab support are described below, for extensive vagrant-libvirt details please [refer to the installation guide](install.html#building-a-libvirt-based-lab).

## Vagrant with VirtualBox

* Most networking vendors don't ship Vagrant boxes, and I had no interest in building VirtualBox boxes from scratch after setting up a *libvirt*-based lab on an Intel NUC. The only boxes I could get with zero hassle were Cisco Nexus 9300v and Arista vEOS, and they both work fine. If you want to add other devices, you'll have to modify *topology-defaults.yml* file.
* The latest version of Arista vEOS available as Vagrant box for VirtualBox is 4.21.14M.
* Vagrantfile created by **create-topology** sets up port forwarding for SSH (22), HTTP (80) and NETCONF (830), but the corresponding Ansible inventory uses contains only **ansible_port** (SSH). You could edit the final inventory by hand, add extra file to `host_vars`, or fix my code. Should you decide to do the latter, please contact me in advance to discuss the necessary data structures.

## Containerlab

* The only device currently supported is Arista cEOS
* Feel free to extend the templates and defaults to support other network devices

## Contributing New Devices

* Get or build Vagrant box
* Add device-specific Vagrantfile configuration to `templates/vagrant/provider/device-domain.j2`
* Add device defaults including Ansible group variables to system **topology-defaults.yml** (within *netsim* directory)
* Add initial device configuration template (based on **ansible_network_os** value) to `templates/initial`
* Optional: add device configuration templates for individual modules. Example: OSPF routing configuration is in `templates/ospf`
* Add configuration deployment task list using device-specific Ansible configuration module to `ansible/deploy-config` directory.
* Add configuration retrieval task list using device-specific Ansible module(s) to `ansible/fetch-config` directory.

Test your changes:

* Create a simple topology using your new device type
* Create Ansible inventory and Vagrantfile with `create-topology -g -i`
* Start your Vagrant environment
* Perform initial device configuration with `initial-config.ansible`
* Log into the device and verify interface state and interface IP addresses

Final steps:

* Fix the documentation (at least install.md and platforms.md)
* Submit a pull request ;)

## Contributing New Virtualization Providers

TBD
