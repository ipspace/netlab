# Building an Arista EOS Vagrant Libvirt Box

Arista EOS is supported by the **netlab libvirt package** command. To build an Arista EOS box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vEOS disk image (.vmdk or .qcow2 file) into that directory
* Execute **netlab libvirt package eos _virtual-disk-file-name_** and follow the instructions

```{warning}
* The **‌netlab libvirt package eos** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config eos** command displays the build recipe:

```{eval-rst}
.. include:: eos.txt
   :literal:
```

## Mutating Virtualbox Boxes

Some releases of Arista vEOS are available as Virtualbox boxes. To use them with *vagrant-libvirt*:

* Install Vagrant *mutate* plugin with **vagrant plugin install vagrant-mutate**
* Download the box file from vendor web site
* Install *virtualbox* version of the box file with **vagrant box add *filename* \-\-name _boxname_**
* Transform *virtualbox* box into *libvirt* box with **vagrant mutate _boxname_ libvirt**
* Remove the _virtualbox_ box with **vagrant box remove _boxname_ \-\-provider virtualbox** command.

```{warning}
You might experience weird Vagrant errors when starting mutated vEOS boxes with **‌vagrant up** or **‌netlab up** command. Building a box yourself usually solves that problem.
```
