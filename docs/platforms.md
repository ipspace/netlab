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

Vagrant providers supported by **config-generate** (require Vagrantfile templates in `templates/vagrant/provider`):

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).
* Rudimentary [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox) support

## VirtualBox Support Limitations

* Most networking vendors don't ship Vagrant boxes, and I had no interest in building VirtualBox boxes from scratch after setting up a *libvirt*-based lab on an Intel NUC. The only boxes I could get with zero hassle were Cisco Nexus 9300v and Arista vEOS.
* Release 0.3 includes VirtualBox Vagrant provider configuration defaults and Vagrantfile templates for Cisco Nexus 9300v and Arista vEOS.
* I couldn't get vEOS to run on my version of Vagrant and VirtualBox on macOS Catalina; Nexus 9300v ran fine. If you manage to get other devices to run on VirtualBox, I'd appreciate pull requests with Vagrantfile snippets.
* Vagrantfile created by **create-topology** sets up port forwarding for SSH (22), HTTP (80) and NETCONF (830), but the corresponding Ansible inventory uses contains only **ansible_port** (SSH). You could edit the final inventory by hand, add extra file to `host_vars`, or fix my code. Should you decide to do the latter, please contact me in advance to discuss the necessary data structures.

## Contributing New Devices

* Get or build Vagrant box
* Add device-specific Vagrantfile configuration to `templates/vagrant/provider/device-domain.j2`
* Add device defaults including Ansible group variables to **topology-defaults.yml**
* Add initial device configuration template (based on **ansible_network_os** value) to `templates/initial`
* Add configuration task list using device-specific configuration module to `ansible/config`.

Test your changes:

* Create a simple topology using your new device type
* Create Ansible inventory and Vagrantfile with `create-topology -g -i`
* Start your Vagrant environment
* Perform initial device configuration with `initial-config.ansible`
* Log into the device and verify interface state and interface IP addresses

Final steps:

* Fix the documentation (at least install.md and platforms.md)
* Submit a pull request ;)
