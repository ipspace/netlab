(build-iosxr)=
# Building a Cisco IOS XR Vagrant Libvirt Box

Cisco IOS XR is supported by the **netlab libvirt package** command. To build an IOS XR box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download IOS XR software and unpack the image archive to get the `qcow2` disk image (example: `xrv9k-fullk9-x-7.4.2.qcow2`).
* Execute **netlab libvirt package iosxr _virtual-disk-file-name_** and follow the instructions.

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process (inspired by [this solution](https://codingpackets.com/blog/cisco-iosxrv-vagrant-libvirt-box-install/)), you'll have to copy-paste the initial device configuration. **netlab libvirt config iosxr** command displays the build recipe:

```{eval-rst}
.. include:: iosxr.txt
   :literal:
```
