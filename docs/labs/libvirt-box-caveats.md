# Box-Building Caveats

The Vagrant box-building process relies on numerous Linux tools whose behavior has changed across Ubuntu releases. These caveats probably no longer apply unless you're using an ancient _netlab_ release older than 1.8.2 (released in May 2024):

* On Ubuntu 22.04 LTS (and later), the `libvirt-qemu` user needs read- and execute access to the VM disk file. It’s easiest to create Vagrant boxes in a subdirectory of the /tmp directory. Starting with release 1.8.2, the **netlab libvirt package** script always builds boxes within the /tmp directory.
* *‌virt-install* might report a fatal error on Ubuntu 22.04 (and later). Execute `export VIRTINSTALL_OSINFO_DISABLE_REQUIRE=1` in your shell and restart the build process. Starting with release 1.8.1, the **netlab libvirt package** script sets this parameter.
* If you downloaded an OVA file, you have to unpack it with the **tar xvf _ova_filename_** command. Starting with release 1.8.2, the **netlab libvirt package** script automatically unpacks the OVA files.

Finally, we tested the box-building scripts on Ubuntu 22.04. The **netlab libvirt package** might not work correctly on other Linux distributions.
