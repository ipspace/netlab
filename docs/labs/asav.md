# Building a Cisco ASAv Vagrant Libvirt Box

Cisco ASAv is supported by the **netlab libvirt package** command. To build a ASAv box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the ASAv disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package asav _virtual-disk-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Preparing the Box Configuration

Initial device configuration is copied from an ISO image created by the installation process. You'll have to set an enable password and save the config. 
**netlab libvirt config asav** command desplays the build recipe (based on the [recipe published by Brad Searle](https://codingpackets.com/blog/cisco-asav-vagrant-libvirt-box-install/)):

```{eval-rst}
.. include:: asav.txt
   :literal:
```

