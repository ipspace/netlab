(build-frr)=
# Building an FRRouting Libvirt Box

By default, _netlab_ uses Debian Vagrant boxes to start FRRouting virtual machines. The Debian boxes do not contain the FRR package (or a few other packages). These packages are installed whenever an FRR VM is started, resulting in significantly longer start times.

You can use the **netlab libvirt package** command to build a custom FRRouting Vagrant box:

* Use the **netlab show images -d frr** to find the Debian release we use for FRR virtual machines
* Download the latest relevant Debian **-generic-amd64.qcow2** image from [Debian Official Cloud Images](https://cloud.debian.org/images/cloud/) (the Bookworm images are [here](https://cloud.debian.org/images/cloud/bookworm/latest/)) into an empty directory
* Execute **netlab libvirt package frr _img-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

**netlab libvirt package** starts the Debian VM and uses **cloud-init** to configure it, install additional software packages, and shut it down.

All you have to do is identify the FRR version that was installed on the VM and pass it to the **netlab libvirt package** command when it asks for the box version. Scroll through the printouts and find the end-of-installation message that should look similar to this:

```
[   21.094634] cloud-init[500]: Installation complete
[   21.095042] cloud-init[500]: =================================
[   21.100452] cloud-init[500]: FRR version installed: 10.5.1
[   21.100844] cloud-init[500]: =================================
```

```{tip}
If the installation process fails, the VM remains running. You can log in as user **vagrant** (password **vagrant**) and investigate the cause of the error (or [open an issue](https://github.com/ipspace/netlab/issues/new/choose)). To disconnect from the VM, use the **virsh** disconnect sequence (usually `Ctrl-]`).
```

After finishing the box-building process, the **netlab libvirt package** command tells you how to use the custom box in a lab topology or as a default FRR box:

```
You created a custom Vagrant box. To use this box in a lab topology, add the
following setting to the lab topology:

defaults.devices.frr.libvirt.image: netlab/frr

Alternatively, use the "netlab defaults" command to set the custom box as the
directory-, project- or user default, for example:

netlab defaults devices.frr.libvirt.image=netlab/frr
```

Finally, use the **netlab libvirt remove --box netlab/frr** command if you want to remove the custom FRR Vagrant box.

## Using a Management VRF

Unline FRR containers, the default or custom-built FRR VM does not have the `eth0` interface in a management VRF. If you want to have the management interface (and the associated default route) on FRR VMs in a management VRF, set the **netlab_mgmt_vrf** parameter with the **[netlab defaults](netlab-defaults)** command:

```
netlab defaults devices.frr.libvirt.group_vars.netlab_mgmt_vrf=True
```

Rebuild the FRR VM after changing the **netlab_mgmt_vrf** parameter. The modified VM will include:

* A management VRF (`mgmt`)
* `eth0` enslaved (according to [Linux docs](https://docs.kernel.org/networking/vrf.html)) to the `mgmt` device
* **sysctl** parameter `net.ipv4.tcp_l3mdev_accept` set to 1 to enable the SSH daemon to accept SSH sessions on VRF interfaces.
