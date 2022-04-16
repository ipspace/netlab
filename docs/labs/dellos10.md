# Building a Dell OS10 Vagrant Libvirt Box

Dell OS10 is supported by the **netlab libvirt package** command.

```{warning}
Dell provides the OS10 Virtual image as a set of vmdk and gns3a files to be used within GNS3, and only for the main release track (i.e., 10.5.2.0). The following procedure will "convert" the required files for using them with Vagrant, and also allows to inject a specific build release into the image (the image is based on a ONIE installer).
```

To prepare for the build:

* Download OS10 files into `/tmp` directory
* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Convert these *vmdk* files into *qcow2* format with *qemu-img* utility:
  * OS10-Disk-1.0.0.vmdk
  * OS10-Installer-`<VERSION>`.vmdk
  * OS10-platform-S4128F-`<VERSION>`.vmdk
```
qemu-img convert -O qcow2 /tmp/OS10-Disk-1.0.0.vmdk OS10-Disk-1.qcow2
qemu-img convert -O qcow2 /tmp/OS10-Installer-10.5.2.0.229.vmdk hdb_OS10-installer.qcow2
qemu-img convert -O qcow2 /tmp/OS10-platform-S4128F-10.5.2.0.229.vmdk hdc_OS10-platform-S4128F.qcow2
```
* Copy the updated Dell OS10 upgrade package (*.bin*) inside the *hdb_OS10-installer.qcow2* disk image:
```
modprobe nbd max_part=8
qemu-nbd --connect=/dev/nbd0 ./hdb_OS10-installer.qcow2

mount /dev/nbd0p1 /mnt/somepoint/

cd /mnt/somepoint/
cp /tmp/PKGS_OS10-Enterprise-10.5.3.4.108buster-installer-x86_64.bin os10.bin
chmod 777 os10.bin
md5sum os10.bin | awk '{print $1}' > image.txt

cd
umount /mnt/somepoint/
qemu-nbd --disconnect /dev/nbd0
```

To build a Dell OS10 box based on the above install image:

* Execute **netlab libvirt package dellos10 OS10-Disk-1.qcow2** and follow the instructions

## Initial Device Configuration

During the box-building process you'll have to copy-paste initial device configuration. **netlab libvirt config dellos10** command displays the build recipe:

```{eval-rst}
.. include:: dellos10.txt
   :literal:
```



