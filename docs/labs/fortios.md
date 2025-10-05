(build-fortios)=
# Building a FortiOS Vagrant Libvirt Box

FortiOS (FortiGate) is supported by the **netlab libvirt package** command. To build a `fortinet/fortios` box:

* Create an empty directory on an Ubuntu machine with *libvirt* and *Vagrant*.
* Copy the FortiGate image (usually a .zip file) into that directory
* If needed, unzip the FortiGate image with **unzip _file_** to get the `fortios.qcow2` disk image.
* Execute **netlab libvirt package fortios _qcow-file-name_** and follow the instructions

```{warning}
* _netlab_ supports FortiGate devices that use username/password to authenticate API calls.
* Before `7.2.0`, the FortiGate VM included a 15 day evaluation license. The vagrant box would need to be recreated 15 days after the initial build to continue using it.
* Starting with `7.2.0`, you can use a permanent evaluation license, linked to your FortiGate Support Portal account.
* Limitations of the evaluation license can be found in the [FortiGate documentation](https://docs.fortinet.com/document/fortigate/7.6.3/administration-guide/441460).
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

The initial device configuration is prepared on a CD-ROM image that is read by the device during the initial boot process. All you have to do is check the applied configuration and shut down the device.

**netlab libvirt config fortios** command displays the build recipe:

```{eval-rst}
.. literalinclude:: fortios.txt
   :language: text
```

```{tip}
If you plan to use a permanent evaluation license, install it before shutting down the FortiGate virtual machine
```
