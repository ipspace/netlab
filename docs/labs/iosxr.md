# Building a Cisco IOS XR Vagrant Libvirt Box

Cisco IOS XR is supported by the **netlab libvirt package** command. To build an IOS XR box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download IOS XR software, and unpack the image archive to get the `qcow2` disk image (example: `xrv9k-fullk9-x-7.4.2.qcow2`).
* Execute **netlab libvirt package iosxr _virtual-disk-file-name_** and follow the instructions.

```{warning}
* The **‌netlab libvirt package csr** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Initial Device Configuration

During the box-building process (inspired by [this solution](https://codingpackets.com/blog/cisco-iosxrv-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config iosxr** command displays the build recipe:

```{eval-rst}
.. include:: iosxr.txt
   :literal:
```
