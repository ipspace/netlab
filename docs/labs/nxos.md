# Building a Cisco Nexus 9300v Vagrant Libvirt Box

Cisco Nexus 9300v is supported by the **netlab libvirt package** command. To build an Nexus 9300v box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download Nexus 9300v disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package nxos _virtual-disk-file-name_** and follow the instructions

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

* Install Vagrant *mutate* plugin with **vagrant plugin install vagrant-mutate**
* Download the box file from vendor web site
* Install *virtualbox* version of the box file with **vagrant box add *filename* \-\-name _boxname_**
* Transform *virtualbox* box into *libvirt* box with **vagrant mutate _boxname_ libvirt**
* Remove the _virtualbox_ box with **vagrant box remove _boxname_ \-\-provider virtualbox** command.

```{warning}
You might experience weird Vagrant errors when starting mutated Nexus OS boxes with **‌vagrant up** or **‌netlab up** command. Building a box yourself usually solves that problem.
```
