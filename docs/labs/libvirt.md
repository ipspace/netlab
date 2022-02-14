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
* [Cisco CSR](csr.md)
* [Cisco Nexus OS](nxos.md)
* [Fortinet FortiOS](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) by [Pete Crocker](https://blog.petecrocker.com/about/)
* [Juniper vSRX 3.0](vsrx.md)
* [Mikrotik RouterOS](http://stefano.dscnet.org/a/mikrotik_vagrant/) by [Stefano Sasso](http://stefano.dscnet.org)
* [VyOS](https://github.com/ssasso/packer-vyos-vagrant) by [Stefano Sasso](http://stefano.dscnet.org)

**Notes:**

* For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.

```{eval-rst}
.. toctree::
   :caption: Box Building Recipes
   :maxdepth: 1
   :hidden:

   csr.md
   eos.md
   nxos.md
   vsrx.md
..
```
