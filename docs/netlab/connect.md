# Connecting to Lab Devices

**netlab connect** command uses information stored in Ansible inventory and reported by **ansible-inventory** command to connect to a lab device using SSH or **docker exec**. You could use it with an inventory file created with **netlab create** command or with any other Ansible inventory.

## Usage

```text
usage: netlab connect [-h] [-v] [-q] [--dry-run] [--snapshot [SNAPSHOT]]
                      [-s SHOW [SHOW ...]]
                      host

Connect to a network device or an external tool

positional arguments:
  host                  Device or tool to connect to

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -q, --quiet           No logging
  --dry-run             Print the commands that would be executed, but do not execute them
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  -s SHOW [SHOW ...], --show SHOW [SHOW ...]
                        Show command to execute on the device

The rest of the arguments are passed to SSH or docker exec command
```

```{tip}
The [**‌--show** option](netlab-connect-show) must be used _after_ the host parameter, as the **‌--show** option consumes all arguments specified after it.
```

## Collecting Device Data

**netlab connect** uses the lab snapshot file (default: `netlab.snapshot.yml`) to read device information. You can overwrite the default snapshot file with the `--snapshot` command line parameter.

## Using Inventory Data

**netlab connect** command uses the following device data (most of it derived from device **group_vars**):

* `ansible_connection`: Use **docker exec** if the connection is set to `docker`[^cd]. Use **ssh** if the connection is set to `ssh`, `paramiko`[^cp], `network_cli`[^cc] or `netconf`[^cn]. Fail for all other connection types.
* `ansible_host`: IP address or alternate FQDN for the lab device (default: host name specified on the command line)
* `ansible_user`: remote username for SSH session (default: not specified)
* `ansible_ssh_pass` to specify password (default: use SSH keys)
* `ansible_port` to specify alternate SSH port (used primarily in VirtualBox environment)
* `netlab_show_command`: command to execute when using `--show` option. Primarily used to deal with FRR/Cumulus Linux running `vtysh` to execute **show** commands.

[^cd]: FRR and Linux devices running under _containerlab_

[^cc]: Devices with traditional networking CLI, including Cisco IOSv, Cisco IOS-XE, Cisco Nexus OS, and Arista EOS.

[^cp]: Linux virtual machines, including Cumulus VX and Nokia SR Linux.

[^cn]: Junos

## Executing a Single Command

Command line parameters specified after the device name are passed to **ssh** or **docker exec** command, allowing you to execute a single command on a lab device.

If you want to process the results of the command executed on a lab device, use **netlab connect -q** to remove the "_we are going to connect to device X_" message.

(netlab-connect-show)=
## Executing a Show Command

You can run **netlab connect** with **--show *args*** option to execute a **show** command on a lab device. In most cases, this is equivalent to running **netlab connect _host_ show _args_** (see above), the major exceptions are FRR and Cumulus Linux.

For example, this is how you could execute **show ip route** command on Cumulus Linux or FRR container without worrying about the FRR `vtysh` details[^PCTC]:

[^PCTC]: The printout contains the actual command needed to execute **show ip route** on FRR. As you can see, it's not exactly trivial.

```
$ netlab connect r2 --show ip route
Connecting to container clab-X-r2, executing sudo vtysh -c "show ip route"
Use vtysh to connect to FRR daemon

Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route, q - queued, r - rejected, b - backup
       t - trapped, o - offload failure
O>* 10.0.0.1/32 [110/20] via 10.1.0.1, swp1, weight 1, 00:23:17
O   10.0.0.2/32 [110/0] is directly connected, lo, weight 1, 00:23:24
C>* 10.0.0.2/32 is directly connected, lo, 00:23:36
O   10.1.0.0/30 [110/10] is directly connected, swp1, weight 1, 00:23:24
C>* 10.1.0.0/30 is directly connected, swp1, 00:23:35
```

## Handling SSH Keys

**netlab connect** command disables SSH host key checking and uses `/dev/null` as _known hosts_ file to simplify lab connectivity (some virtual devices change SSH key on every restart).

```{warning}
Do not use **netlab connect** in production environment.
```
