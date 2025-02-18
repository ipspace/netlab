(build-fortios)=
# Building a FortiOS Vagrant Libvirt Box

FortiOS (FortiGate) is supported by the **netlab libvirt package** command. To build a `fortinet/fortios` box:

* Create an empty directory on an Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the FortiGate image (usually a .zip file) into that directory
* If needed, unzip the FortiGate image with **unzip _file_** to get the `fortios.qcow2` disk image.
* Execute **netlab libvirt package fortios _qcow-file-name_** and follow the instructions

```{warning}
* _netlab_ supports FortiGate devices that use username/password to authenticate API calls. The last software releases known to work are 7.0.x and 7.2.0.
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

You'll have to copy-paste initial device configuration during the box-building process. **netlab libvirt config fortios** command displays the build recipe:

```{eval-rst}
.. include:: fortios.txt
   :literal:
```

```{tip}
If you plan to use a permanent evaluation license, install it before shutting down the FortiGate virtual machine
```
