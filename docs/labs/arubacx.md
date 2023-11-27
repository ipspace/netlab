# Building an ArubaOS-CX Libvirt Box

Aruba AOS-CX 10 is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the `Aruba_AOS-CX_Switch_Simulator` (*see below*) OVA image into that directory, and uncompress it (and the OVA file - which is a tarball)
* Convert the vmdk image to the *qcow2* format (`qemu-img convert -f vmdk -O qcow2 arubaoscx-disk-image-genericx86-p4-20231110145644.vmdk arubacx-10.13.qcow2`)
* Execute **netlab libvirt package arubacx _virtual-disk-file-name_** and follow the instructions

```{warning}
* The **‌netlab libvirt package arubacx** command has been tested on Ubuntu 20.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Aruba AOS-CX download notes

The *Aruba AOS-CX 10 Switch Simulator* image can be download from the *Aruba Support Portal* (after user registration), searching for: `Aruba_AOS-CX_Switch_Simulator`. In example, release **10.13** can be downloaded from [here](https://asp.arubanetworks.com/downloads/software/RmlsZTowOTRjZDU3ZS04Y2VkLTExZWUtOGRiNy0yMzkyMDY4ZjdmZmU%3D).

## Initial Device Configuration

During the box-building process you'll have to copy-paste initial device configuration. **netlab libvirt config arubacx** command displays the build recipe:

```{eval-rst}
.. include:: arubacx.txt
   :literal:
```
**NOTE**: It seems it's not possible to create a user called *vagrant* on AOS-CX, so the configuration creates a *netlab* user (with password: *netlab*).

## Ansible Galaxy for Aruba AOS-CX

You need to install the Ansible modules for Aruba AOS-CX with: `ansible-galaxy collection install arubanetworks.aoscx`.
