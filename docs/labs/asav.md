# Building a Cisco ASAv Vagrant Libvirt Box

Cisco ASAv is supported by the **netlab libvirt package** command. To build a ASAv box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the ASAv disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package asav _virtual-disk-file-name_** and follow the instructions

## Preparing the Box Configuration

Initial device configuration is copied from an ISO image created by the installation process. You'll have to set an enable password and save the config. 
**netlab libvirt config asav** command desplays the build recipe (based on the [recipe published by Brad Searle](https://codingpackets.com/blog/cisco-asav-vagrant-libvirt-box-install/)):

```{eval-rst}
.. include:: asav.txt
   :literal:
```

