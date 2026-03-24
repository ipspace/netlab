(build-exos)=
# Building an Extreme Networks EXOS Vagrant Libvirt Box

Extreme Networks EXOS is supported by the **netlab libvirt package** command. To build an EXOS box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download EXOS disk image (.qcow2 file) into that directory.

```{tip}
Select and download the QCOW2 image from [Extreme Networks github page](https://github.com/extremenetworks/Virtual_EXOS?tab=readme-ov-file#qcow2-files-for-gns3)

Then copy the URL of the QCOW2 image and use `curl -O <URL>` to download it.
```

* Execute **netlab libvirt package exos _virtual-disk-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process you'll have to copy-paste initial device configuration. **netlab libvirt config exos** command displays the build recipe.

```{eval-rst}
.. include:: exos.txt
   :literal:
```
