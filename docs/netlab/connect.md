# Connecting to Lab Devices

**netlab connect** command uses information stored in Ansible inventory and reported by **ansible-inventory** command to connect to a lab device using SSH or **docker exec**. You could use it with an inventory file created with **netlab create** command or with any other Ansible inventory.

## Usage

```text
usage: netlab connect [-h] [-v] host

Connect to a network device

positional arguments:
  host           Device to connect to

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Verbose logging
  -d, --devices  Use netlab-devices.yml as inventory source

The rest of the arguments are passed to SSH or docker exec command
```

## Collecting Inventory Data

When run with `--devices` argument, **netlab connect** reads inventory data from `netlab-devices.yml` file[^1]. You can override the default file name with `NETLAB_DEVICES` environment variable.

In all other cases, **netlab connect** uses **ansible-inventory** command to fetch device data from Ansible inventory.

[^1]: *netlab-devices.yml* inventory uses Ansible naming convention and contains information very similar to what **ansible-inventory** would return.

## Using Inventory Data

**netlab connect** command uses the following device inventory variables:

* `ansible_connection`: Use **docker exec** if the connection is set to `docker`[^cd]. Use **ssh** if the connection is set to `ssh`, `paramiko`[^cp], `network_cli`[^cc] or `netconf`[^cn]. Fail for all other connection types.
* `ansible_host`: IP address or alternate FQDN for the lab device (default: host name specified on the command line)
* `ansible_user`: remote username for SSH session (default: not specified)
* `ansible_ssh_pass` to specify password (default: use SSH keys)
* `ansible_port` to specify alternate SSH port (used primarily in VirtualBox environment)

[^cd]: FRR and Linux devices running under _containerlab_

[^cc]: Devices with traditional networking CLI, including Cisco IOSv, Cisco IOS-XE, Cisco Nexus OS, and Arista EOS.

[^cp]: Linux virtual machines, including Cumulus VX and Nokia SR Linux.

[^cn]: Junos

## Executing a Single Command

Command line parameters specified after the device name are passed to **ssh** or **docker exec** command, allowing you to execute a single command on a lab device.

## Handling SSH Keys

**netlab connect** command disables SSH host key checking and uses `/dev/null` as _known hosts_ file to simplify lab connectivity (some virtual devices change SSH key on every restart).

```{warning}
Do not use **netlab connect** in production environment.
```
