# Install System Software

**netlab install** uses internal installation scripts to install nice-to-have Ubuntu software, Ansible and related networking libraries, or libvirt+vagrant.

The *ubuntu* and *libvirt* installation scripts run only on Ubuntu (they were tested on Ubuntu 20.04), the *ansible* installation script should run in any environment with **bash** and **pip3**.

## Usage

```text
usage: netlab install [-h] [-v] [-q] [-y]
                      [{ubuntu,ansible,libvirt} [{ubuntu,ansible,libvirt} ...]]

Install additional software

positional arguments:
  {ubuntu,ansible,libvirt}
                        Run the specified installation script

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -q, --quiet           Be as quiet as possible
  -y, --yes             Run the script without prompting for a confirmation
```

## Installation Scripts

* *ubuntu* script installs Python3 development components that might be needed for Ansible installation, common tools like **git** and **sshpass**, and XML libraries
* *ansible* script uses **pip** to install the latest version of Ansible, networking libraries (*netaddr, paramiko, netmiko*), text parsing libraries (*testfsm, ttp, ntc-templates*), and a few other utility libraries (*jmespath, yamllint, yq*)
* *libvirt* script installs *libvirt* and supporting libraries/packages, *vagrant*, *vagrant-libvirt* plugin, and creates the *vagrant-libvirt* virtual network.

