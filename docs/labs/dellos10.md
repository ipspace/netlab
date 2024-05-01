(build-dellos10)=
# Building a Dell OS10 Vagrant Libvirt Box

Dell OS10 is supported by the **netlab libvirt package** command.

```{warning}
* Dell [provides the OS10 Virtual image](https://www.dell.com/support/home/en-us/product-support/product/smartfabric-os10-emp-partner/drivers) as a ZIP archive `.vmdk` and `.gns3a` files. **netlab libvirt package** converts these files into a Vagrant box.
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

* Download the OS10 ZIP archive into an empty directory
* Unzip the archive with the **unzip *zip-file-name*** command
* Execute **netlab libvirt package dellos10 OS10-Disk-1.0.0.vmdk**[^NCFN] and follow the instructions

[^NCFN]: Hoping Dell doesn't decide to change the filename ;)

```{tip}
The box-building process creates a Vagrant box based on the S5224F platform. If you'd like to work with a different switch model, you'll have to fix the installation script; if you make the platform selection configurable, please submit a Pull Request.
```

## Initial Device Configuration

You'll have to copy-paste the initial device configuration during the box-building process. **netlab libvirt config dellos10** command displays the build recipe:

```{eval-rst}
.. include:: dellos10.txt
   :literal:
```

## Ansible Galaxy for Dell OS10

You must install the Ansible modules for Dell OS10 with the  `ansible-galaxy collection install dellemc.os10` command.


