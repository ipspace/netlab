# Supported Platforms

Virtual network devices supported by **config-generate** (require `topology-defaults.yml` settings and Vagrantfile templates in `templates/vagrant/provider`):

* Cisco IOSv
* Cisco CSR1000v
* Cisco Nexus 9300v
* Arista vEOS
* Arrcus ArcOS

Network operating systems supported by **config.ansible** (require device-specific task list in `ansible/config`):

* Cisco IOS
* Cisco Nexus OS
* Cisco Nexus 9300v
* Arista EOS
* Arrcus ArcOS

Network operating systems supported by **initial-config.ansible** (require **config.ansible** support and initial device configuration template in `templates/initial`):

* Cisco IOS (IOSv and CSR 1000v)
* Cisco Nexus OS (Nexus 9300v)
* Arista EOS (vEOS)
* Arrcus ArcOS

Vagrant providers supported by **config-generate** (require Vagrantfile templates in `templates/vagrant/provider`):

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).

## Contributing new devices

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

* Submit a pull request ;)
