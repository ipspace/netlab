# Create Vagrant Boxes for Libvirt/KVM Environment

Vagrant starts virtual machines from prepackaged VM images called *boxes*. While it's possible to download some network device images from Vagrant Cloud, you'll have to build most of the boxes you'd want to use in your lab.

You have to use the following box names when installing or building the Vagrant boxes (see [supported platforms](../platforms.md) and **[netlab show images](../netlab/show.md)** for more details):

| Virtual network device | Vagrant box name            |
| ---------------------- | --------------------------- |
| Arista vEOS            | arista/veos                 |
| Cisco ASAv             | cisco/asav                  |
| Cisco IOSv             | cisco/iosv                  |
| Cisco CRS 1000v        | cisco/csr1000v              |
| Cisco Nexus 9300v      | cisco/nexus9300v            |
| Dell OS10              | dell/os10                   |
| Fortinet FortiOS       | fortinet/fortios            |
| Juniper vSRX 3.0       | juniper/vsrx3               |
| Mikrotik RouterOS 6    | mikrotik/chr                |
| Mikrotik RouterOS 7    | mikrotik/chr7               |

The following Vagrant boxes are automatically downloaded from Vagrant Cloud when you're using them for the first time in your lab topology:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Cumulus VX             | CumulusCommunity/cumulus-vx:4.4.0 |
| Cumulus VX 5.0 (NVUE)            | CumulusCommunity/cumulus-vx:5.0.1 |
| Generic Linux          | generic/ubuntu2004 |
| VyOS                   | vyos/current       |

**NOTE**: Even if a new box version is available from Vagrant Cloud, Vagrant will only output a warning to the user letting them know an update is available. That user can choose to ignore the warning for now, or can update the box by running `vagrant box update`. 
Vagrant can not and does not automatically download the updated box and update the machine because boxes can be relatively large (See: https://www.vagrantup.com/docs/boxes/versioning).

However, we recommend to periodically download the updated box for:
* vyos/current

## Building Your Own Boxes

* [Arista vEOS](eos.md)
* [Cisco ASAv](asav.md)
* [Cisco IOSv](iosv.md)
* [Cisco CSR](csr.md)
* [Cisco Nexus OS](nxos.md)
* [Dell OS10](dellos10.md) by [Stefano Sasso](http://stefano.dscnet.org)
* [Fortinet FortiOS](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) by [Pete Crocker](https://blog.petecrocker.com/about/)
* [Juniper vSRX 3.0](vsrx.md)
* [Mikrotik RouterOS 7](routeros7.md) - based on the original [Mikrotik RouterOS](http://stefano.dscnet.org/a/mikrotik_vagrant/) by [Stefano Sasso](http://stefano.dscnet.org)
* [VyOS](https://github.com/ssasso/packer-vyos-vagrant) by [Stefano Sasso](http://stefano.dscnet.org) - if you don't want to use the one from Vagrant Cloud.

```{note}
For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.
```

## Replacing Vagrant Boxes

If you want to rebuild and install a Vagrant box with the same version number, you have to remove the old box manually. You also have to delete the corresponding volume (disk image) from *libvirt* storage pool (*vagrant-libvirt* plugin installs new boxes but does not clean up the old ones).

To delete an old version of a Vagrant box use a procedure  similar to the one described below:

* Use `vagrant box list` to list the installed boxes
* Use `vagrant box remove <box-name> --box-version=<box-version>` to delete the Vagrant box[^VV]
* Use `virsh vol-list --pool default`[^DP] to list the installed Vagrant boxes
* Find the relevant volume name, for example, `cisco-VAGRANTSLASH-iosxr_vagrant_box_image_7.4.2_box.img` for an IOS XR 7.4.2 image
* Delete the volume with `virsh vol-delete --pool default <volume-name>`

[^VV]: You don't have to specify the box version unless you created multiple versions of the same box.

[^DP]: *libvirt* environment created with the **netlab install libvirt** installation script uses the *default* storage pool. A custom installation might use a different storage pool name.

The new Vagrant box will be copied into the *libvirt* storage pool the next time you'll use the affected device in your lab.

```{eval-rst}
.. toctree::
   :caption: Box Building Recipes
   :maxdepth: 1
   :hidden:

   eos.md
   asav.md
   csr.md
   iosv.md
   nxos.md
   dellos10.md
   vsrx.md
   routeros7.md
..
```
