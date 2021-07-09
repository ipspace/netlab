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

The rest of the arguments are passed to SSH or docker exec command
```

## Information Collected from Ansible Inventory

**netlab connect** command uses the following Ansible inventory variables:

* `ansible_connection`: use **docker exec** instead of **ssh** if the connection is set to `docker`
* `ansible_host`: IP address or alternate FQDN for the lab device (default: host name specified on the command line)
* `ansible_user`: remote username for SSH session (default: not specified)
* `ansible_ssh_pass` to specify password (default: use SSH keys)
* `ansible_port` to specify alternate SSH port (used primarily in VirtualBox environment)

## Executing a Single Command

Command line parameters specified after the device name are passed to **ssh** or **docker exec** command, allowing you to execute a single command on a lab device.

## Handling SSH Keys

**netlab connect** command disables SSH host key checking and uses `/dev/null` as _known hosts_ file to simplify lab connectivity (some virtual devices change SSH key on every restart).

```{warning}
Do not use **netlab connect** in production environment.
```
