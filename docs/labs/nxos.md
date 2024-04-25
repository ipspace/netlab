# Cisco Nexus 9300v Vagrant Libvirt Boxes

You can download Nexus 9300v virtual disk (`.qcow2` file) or Vagrant box for VirtualBox from software.cisco.com. Vagrant box created for VirtualBox can be mutated into a *libvirt* box with `vagrant-mutate` plugin.

Mutated NX-OS 9.3.10 box works well with `vagrant-libvirt`. You might want to try the same process with other NX-OS software releases before building your own Nexus 9300v box.

## Mutating a VirtualBox Box

* Download `nexus9300v.<release>.box` file from software.cisco.com
* Check whether the `vagrant-mutate` plugin is installed with `vagrant plugin list`
* If needed, install the `vagrant-mutate` plugin with `vagrant plugin install vagrant-mutate`
* Install *virtualbox* version of the Nexus 9300v Vagrant box with `vagrant box add <box-filename> --name cisco/nexus9300v`
* Mutate the Nexus 9300v box with `vagrant mutate cisco/nexus9300v libvirt`
* Verify that you got the desired Vagrant box installed with `vagrant box list`
* Optionally remove the *virtualbox* version of the Vagrant box with `vagrant box remove cisco/nexus9300v --provider virtualbox`

## Building a Cisco Nexus 9300v Vagrant Libvirt Box

Cisco Nexus 9300v is supported by the **netlab libvirt package** command. To build an Nexus 9300v box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download Nexus 9300v disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package nxos _virtual-disk-file-name_** and follow the instructions

```{warning}
* The box building process generates a random device serial number that will be used by all Nexus 9300v devices created from the Vagrant box. As NX-OS uses device serial number as its DHCP client ID, you might experience problems starting a lab with more than one Nexus 9300v device on newer versions of KVM/libvirt. The workaround-of-last-resort is [setting libvirt **batch_size** to 1](libvirt.md#starting-virtual-machines-in-batches).
* The **‌netlab libvirt package nxos** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
```

```{tip}
See [Cisco Nexus OS Caveats](../caveats.md#cisco-nexus-os) if you want to run NX OS 10.1 or later
```

## Initial Device Configuration

During the box-building process (inspired by [this solution](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt)) you'll have to copy-paste initial device configuration. **netlab libvirt config nxos** command displays the build recipe:

```{eval-rst}
.. include:: nxos.txt
   :literal:
```

## Mutating Virtualbox Boxes

Cisco Nexus 9300v is available as Virtualbox box. To use that box with *vagrant-libvirt*:


```{warning}
You might experience weird Vagrant errors when starting mutated Nexus OS boxes with **‌netlab up** command. Building a box yourself usually solves that problem.
```
