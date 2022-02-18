# Building a Cisco IOSv Vagrant Libvirt Box

Cisco IOSv is supported by the **netlab libvirt package** command. To build a IOSv box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the IOSv disk image (.vmdk file) into that directory
* Execute **netlab libvirt package iosv _virtual-disk-file-name_** and follow the instructions

## Initial Device Configuration

During the box-building process (inspired by [this recipe](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config iosv** command displays the build recipe:

```{eval-rst}
.. include:: iosv.txt
   :literal:
```
