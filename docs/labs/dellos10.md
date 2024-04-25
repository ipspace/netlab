# Building a Dell OS10 Vagrant Libvirt Box

Dell OS10 is supported by the **netlab libvirt package** command.

```{warning}
* Dell provides the OS10 Virtual image as a set of vmdk and gns3a files to be used within GNS3. The following procedure will "convert" the required files for using them with Vagrant.
* The **‌netlab libvirt package dellos10** command has been tested on Ubuntu and might not work on other Linux distros.
* *‌virt-install* might report a fatal error on Ubuntu 22.04. Execute `export VIRTINSTALL_OSINFO_DISABLE_REQUIRE=1` in your shell and restart the build process.
```

To prepare for the build:

* Download OS10 files into `/tmp` directory
* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Convert these *vmdk* files into *qcow2* format with *qemu-img* utility:
  * OS10-Disk-1.0.0.vmdk
  * OS10-Installer-`<VERSION>`.vmdk
  * OS10-platform-`<PLATFORM>`-`<VERSION>`.vmdk
```
qemu-img convert -O qcow2 /tmp/OS10-Disk-1.0.0.vmdk OS10-Disk-1.qcow2
qemu-img convert -O qcow2 /tmp/OS10-Installer-10.5.3.4.108.vmdk hdb_OS10-installer.qcow2
qemu-img convert -O qcow2 /tmp/OS10-platform-S5224F-10.5.3.4.108.vmdk hdc_OS10-platform.qcow2
```

To build a Dell OS10 box based on the above install image:

* Execute **netlab libvirt package dellos10 OS10-Disk-1.qcow2** and follow the instructions

## Initial Device Configuration

During the box-building process you'll have to copy-paste initial device configuration. **netlab libvirt config dellos10** command displays the build recipe:

```{eval-rst}
.. include:: dellos10.txt
   :literal:
```



