(build-iosvl2)=
# Building a Cisco IOSv Layer-2 Vagrant Libvirt Box

Cisco [IOSvL2](https://developer.cisco.com/docs/modeling-labs/iosvl2/#iosvl2) is supported by the **netlab libvirt package** command. To build an IOSvL2 box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the IOSvL2 disk image (`.vmdk` or `.qcow` file) into that directory. The image name should start with `vios_l2` or you might not have an IOSv Layer-2 image.
* Execute **netlab libvirt package iosvl2 _virtual-disk-file-name_** and follow the instructions

```{warning}
* The Cisco IOSv layer-2 image uses slightly different configuration commands and system defaults than the IOSv image and must be built as a separate Vagrant box.
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process (inspired by [this recipe](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config iosvl2** command displays the build recipe:

```{eval-rst}
.. include:: iosvl2.txt
   :literal:
```
