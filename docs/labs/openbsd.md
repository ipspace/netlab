(build-openbsd)=
# Building an OpenBSD Libvirt Box

You can use the **netlab libvirt package** command to build a OpenBSD Vagrant box:

* Download the OpenBSD **qcow2** image from https://bsd-cloud-image.org/ into an empty directory
* Execute **netlab libvirt package openbsd _img-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

The OpenBSD VM is configured with **cloud-init**, but you still have to perform a controlled shutdown before the virtual disk is packed into a Vagrant box.

The **netlab libvirt config openbsd** command displays the build recipe:

```{eval-rst}
.. include:: openbsd.txt
   :literal:
```
