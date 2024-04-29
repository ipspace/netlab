# Building a Dell OS10 Vagrant Libvirt Box

Dell OS10 is supported by the **netlab libvirt package** command.

```{warning}
* Dell provides the OS10 Virtual image as a set of vmdk and gns3a files to be used within GNS3. The following procedure will "convert" the required files for using them with Vagrant.
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
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

## Ansible Galaxy for Dell OS10

You must install the Ansible modules for Dell OS10 with the  `ansible-galaxy collection install dellemc.os10` command.


