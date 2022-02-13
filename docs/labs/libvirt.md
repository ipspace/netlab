# Create Vagrant Boxes for Libvirt/KVM Environment

Vagrant starts virtual machines from prepackaged VM images called *boxes*. While it's possible to download some network device images from Vagrant Cloud, you'll have to build most of the boxes you'd want to use in your lab.

You have to use the following box names when installing or building the Vagrant boxes (see [supported platforms](../platforms.md) for more details):

| Virtual network device | Vagrant box name            |
| ---------------------- | --------------------------- |
| Arista vEOS            | arista/veos                 |
| Cisco IOSv             | cisco/iosv                  |
| Cisco CRS 1000v        | cisco/csr1000v              |
| Cisco Nexus 9300v      | cisco/nexus9300v            |
| Fortinet FortiOS       | fortinet/fortios            |
| Juniper vSRX 3.0       | juniper/vsrx3               |
| VyOS                   | vyos/vyos                   |
| Mikrotik CHR RouterOS  | mikrotik/chr                |

The following Vagrant boxes are automatically downloaded from Vagrant Cloud when you're using them for the first time in your lab topology:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Cumulus VX             | CumulusCommunity/cumulus-vx:4.4.0 |
| Cumulus VX 5.0 (NVUE)            | CumulusCommunity/cumulus-vx:5.0.1 |
| Generic Linux          | generic/ubuntu2004 |

## Building Your Own Boxes

* [Arista vEOS](eos.md)
* [Cisco IOSv](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/) by [Brad Searle](https://codingpackets.com)
* [Cisco CSR](https://codingpackets.com/blog/cisco-csr-1000v-vagrant-libvirt-box-install/) by [Brad Searle](https://codingpackets.com)
* [Cisco Nexus OS](nxos.md)
* [Fortinet FortiOS](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) by [Pete Crocker](https://blog.petecrocker.com/about/)
* [Juniper vSRX 3.0](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/) by [Brad Searle](https://codingpackets.com) [[notes](#notes-on-juniper-vsrx-vagrantfile-template)]
* [Mikrotik RouterOS](http://stefano.dscnet.org/a/mikrotik_vagrant/) by [Stefano Sasso](http://stefano.dscnet.org)
* [VyOS](https://github.com/ssasso/packer-vyos-vagrant) by [Stefano Sasso](http://stefano.dscnet.org)

**Notes:**

* If you're experiencing high CPU utilization with Cisco CSR, [set halt_poll_ns to zero](https://codingpackets.com/blog/kvm-host-high-cpu-fix/).
* For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.

## Notes on Juniper vSRX Vagrantfile template

The Vagrant template for vSRX uses _default\_prefix_ libvirt parameter to set the domain (VM) name and uses the VM name to set libvirt vCPU quota.

The template has been tested with Vagrant version 2.2.14. Some earlier versions of Vagrant generated VM names using a slightly different algorithm (the underscore between _default\_prefix_ and VM name was added automatically) and might thus generate an unexpected VM name. To fix that problem remove parts of **vsrx-domain.j2** template:

* Remove _domain.default\_prefix_ parameter (default value should generate the expected VM name) or
* Remove the whole CPU-limiting logic (trading CPU cycles for simplicity)

```{eval-rst}
.. toctree::
   :caption: Box Building Recipes
   :maxdepth: 1
   :hidden:

   eos.md
   nxos.md
..
```
