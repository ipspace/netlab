(build-sonic)=
# Building a Sonic Vagrant Libvirt Box

You can use the **netlab libvirt package** command to build a Sonic Vagrant box for a Sonic virtual machine:

* Download the **sonic-vs.img.gz** image from Azure or [sonic.software](https://sonic.software/) into an empty directory.
* Unzip image with **gunzip _gz-file-name_**.
* Execute **netlab libvirt package sonic _img-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process, you might have to disable ZTP or clean up the initial configuration database. The **netlab libvirt config sonic** command displays the build recipe:

```{eval-rst}
.. include:: sonic.txt
   :literal:
```
