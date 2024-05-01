(build-arubacx)=
# Building an ArubaOS-CX Libvirt Box

Aruba AOS-CX 10 is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the `Aruba_AOS-CX_Switch_Simulator` (*see below*) OVA image into that directory.
* Starting with the *netlab* release 1.8.2, execute **netlab libvirt package arubacx _ova-file-name_**
* If you're using a *netlab* release older than 1.8.2, unpack the OVA file with **tar xvf _ova-file-name_** and execute **netlab libvirt package arubacx _vmdk-disk-file-name_**
* Follow the instructions given by the **netlab libvirt package** script

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Aruba AOS-CX download notes

The *Aruba AOS-CX 10 Switch Simulator* image can be downloaded from the *Aruba Support Portal* (requires user registration). Search for the `Aruba_AOS-CX_Switch_Simulator`. For example, the release **10.13** can be downloaded from [here](https://networkingsupport.hpe.com/downloads/software/RmlsZToyOGE0NDJmYS1jMDgxLTExZWUtYmJjMi01ZmNmNDVkNDc4NDk%3D).

## Initial Device Configuration

You'll have to copy-paste the initial device configuration during the box-building process. The **netlab libvirt config arubacx** command displays the build recipe:

```{eval-rst}
.. include:: arubacx.txt
   :literal:
```

**NOTE**: It seems impossible to create a user called *vagrant* on AOS-CX, so the configuration creates a *netlab* user (with password: *netlab*).

## Ansible Galaxy for Aruba AOS-CX

You must install the Ansible modules for Aruba AOS-CX with the  `ansible-galaxy collection install arubanetworks.aoscx` command.
