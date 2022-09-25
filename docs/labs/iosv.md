# Building a Cisco IOSv Vagrant Libvirt Box

Cisco IOSv is supported by the **netlab libvirt package** command. To build a IOSv box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the IOSv disk image (.vmdk file) into that directory
* Execute **netlab libvirt package iosv _virtual-disk-file-name_** and follow the instructions

```{warning}
* The **‌netlab libvirt package ios** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Initial Device Configuration

During the box-building process (inspired by [this recipe](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config iosv** command displays the build recipe:

```{eval-rst}
.. include:: iosv.txt
   :literal:
```
