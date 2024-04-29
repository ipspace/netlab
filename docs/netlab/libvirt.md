# Libvirt Utilities

**netlab libvirt** performs these *libvirt*-related functions:

* **package** -- create a Vagrant box from a VM virtual disk in `qcow2` or `vmdk` format.
* **config** -- display box building recipe.

```text
% netlab libvirt

Usage:

    netlab libvirt <action> <parameters>

The 'netlab libvirt' command can execute the following actions:

package   Help you create a Vagrant box from a qcow/vmdk virtual disk
config    Print the build recipe for the specified Vagrant box

Use 'netlab libvirt <action> --help' to get action-specific help
```

(netlab-libvirt-package)=
## Building a Vagrant Box

The **netlab libvirt package** command:

* Creates a temporary build directory under the `/tmp` directory
* Copies the specified virtual disk into the build directory.
* Starts a VM from the copied virtual disk and connects your terminal to its console
* When you disconnect from the VM (follow the build recipe), stops and destroys the VM and builds a Vagrant box
* Asks you for the software version you're using and installs the Vagrant box

```
usage: netlab libvirt package [-h] [-v] [-q]
              {arubacx,asav,csr,dellos10,eos,iosv,iosxr,nxos,routeros7,vptx,vsrx}
              disk

Package a virtual machine into a libvirt Vagrant box

positional arguments:
  {arubacx,asav,csr,dellos10,eos,iosv,iosxr,nxos,routeros7,vptx,vsrx}
                        Network device you want to create
  disk                  Virtual machine disk (vmdk or qcow2)

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
```
