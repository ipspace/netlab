(netlab-status)=
# Display Running Lab Instances

**netlab status** command displays the running lab instances and the provider-specific workloads (*[libvirt](../labs/libvirt.md)* virtual machines or *[containerlab](../labs/clab.md)* containers).

This command uses the *netlab* status file (default: `~/.netlab/status.yml`) to get the state of running lab instances and [provider-specific status commands](netlab-status-provider) to get the workload state. The status file is updated by **netlab up** and **netlab down** commands.

## Usage

```
usage: netlab status [-h] [-l] [--cleanup] [--reset] [--format {json,yaml,text}]
                     [--memory] [--all] [-v] [-q] [-i INSTANCE]

Display lab status

options:
  -h, --help            show this help message and exit
  -l, --log             Display the lab instance event log
  --cleanup             Cleanup the current or specified lab instance
  --reset               Reset the lab instance tracking system
  --format {json,yaml,text}
                        Specify the output format
  --memory              Include memory utilization statistics
  --all                 Display an overview of all lab instance(s)
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  -i, --instance INSTANCE
                        Specify the lab instance to inspect
```

* **netlab status** displays the status and workload (VMs or containers) of the current or selected lab instance. Add the **--memory** option to include VM/container memory utilization.
* **netlab status --all** displays an overview of all currently running lab instances.
* **netlab status --log** displays the detailed status log (including state changes and executed commands) of the current or selected lab instance(s)
* **netlab status --cleanup** shuts down selected lab instance(s). It changes the current directory to the lab directory saved in the status file and executes **netlab down --cleanup** in that directory
* **netlab status --reset** deletes the status file. Use this command only if the status file becomes corrupted.

```{tip}
You can use the `--format json` or `--format yaml` option to display the lab status in an automation-friendly format
```

## Display Lab Instance State

The **netlab status** command displays the selected lab instance and its VMs and containers:

```
Lab default in /home/user
  status:      started
  topology:    /home/user/tools/tests/integration/bgp/04-originate.yml
  provider(s): libvirt,clab

┏━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ node ┃ device  ┃ image                        ┃ mgmt IP         ┃ connection  ┃ provider ┃ VM/container ┃ status     ┃
┡━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ dut  │ arubacx │ aruba/cx                     │ 192.168.121.101 │ network_cli │ libvirt  │ bgp_dut      │ running    │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┤
│ dut2 │ arubacx │ aruba/cx                     │ 192.168.121.102 │ network_cli │ libvirt  │ bgp_dut2     │ running    │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┤
│ x1   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.103 │ docker      │ clab     │ clab-bgp-x1  │ Up 3 hours │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┤
│ x2   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.104 │ docker      │ clab     │ clab-bgp-x2  │ Up 3 hours │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┤
│ r1   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.105 │ docker      │ clab     │ clab-bgp-r1  │ Up 3 hours │
└──────┴─────────┴──────────────────────────────┴─────────────────┴─────────────┴──────────┴──────────────┴────────────┘
```

With the `--memory` option, the printout includes the VM/container memory utilization:

```
Lab default in /home/user
  status:      started
  topology:    /home/user/tools/tests/integration/bgp/04-originate.yml
  provider(s): libvirt,clab
  memory used: 3.473GiB

┏━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ node ┃ device  ┃ image                        ┃ mgmt IP         ┃ connection  ┃ provider ┃ VM/container ┃ status     ┃ memory   ┃
┡━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ dut  │ arubacx │ aruba/cx                     │ 192.168.121.101 │ network_cli │ libvirt  │ bgp_dut      │ running    │ 1.708GiB │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┼──────────┤
│ dut2 │ arubacx │ aruba/cx                     │ 192.168.121.102 │ network_cli │ libvirt  │ bgp_dut2     │ running    │ 1.692GiB │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┼──────────┤
│ x1   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.103 │ docker      │ clab     │ clab-bgp-x1  │ Up 3 hours │ 22.66MiB │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┼──────────┤
│ x2   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.104 │ docker      │ clab     │ clab-bgp-x2  │ Up 3 hours │ 22.63MiB │
├──────┼─────────┼──────────────────────────────┼─────────────────┼─────────────┼──────────┼──────────────┼────────────┼──────────┤
│ r1   │ frr     │ quay.io/frrouting/frr:10.6.1 │ 192.168.121.105 │ docker      │ clab     │ clab-bgp-r1  │ Up 3 hours │ 29.77MiB │
└──────┴─────────┴──────────────────────────────┴─────────────────┴─────────────┴──────────┴──────────────┴────────────┴──────────┘
```

(netlab-status-provider)=
```{tip}
* **‌netlab status** executes **‌vagrant status --machine-readable** to get the status of Vagrant-controlled virtual machines and **‌docker ps** to get the status of running containers. The **vagrant status‌** might take a few seconds when executed on large labs and significantly longer if Vagrant cannot determine the state of a virtual machine (returning **‌inaccessible**).
* **‌netlab status --memory** executes **‌virsh domstats** and **‌docker stats**. At least the **‌docker stats** command is not blazingly fast.
* The **‌virsh domstats** reports the Resident Set Size (RSS) of the QEMU process running the virtual machine (the physical RAM allocation), not the amount of virtual RAM allocated to the virtual machine.
* With Linux Kernel Samepage Merging (KSM) enabled, the reported memory utilization overstates the real usage. 
```

## Display Lab Instance Log

The **netlab status --log** command displays a detailed lab instance log, including state changes and executed commands:

```
$ netlab status --log
Lab default in /home/pipi/net101/tools/X
  status: started
  provider(s): clab

2024-03-21T15:49:53.405969+00:00: OK: containerlab version
2024-03-21T15:49:53.428919+00:00: OK: bash -c [[ `containerlab version|awk '/version/ {print $2}'` > '0.42' ]] && echo OK
2024-03-21T15:49:53.430807+00:00: restarting lab
2024-03-21T15:49:53.432369+00:00: starting provider clab
2024-03-21T15:49:56.009208+00:00: OK: sudo -E containerlab deploy -t clab.yml
2024-03-21T15:49:56.011297+00:00: clab workload started
2024-03-21T15:49:56.014699+00:00: deploying initial configuration
2024-03-21T15:49:56.405222+00:00: deploying configuration: complete configuration
2024-03-21T15:50:01.851112+00:00: OK: ansible-playbook /home/pipi/net101/tools/netsim/ansible/initial-config.ansible
2024-03-21T15:50:01.893476+00:00: OK: netlab initial --no-message
2024-03-21T15:50:01.895433+00:00: initial configuration complete
2024-03-21T15:50:01.897105+00:00: started
```

## Running Lab Instances

The **netlab status --all** command displays all running lab instances[^LI], their working directories, and the virtual machines (domains) and containers running on the current server.

[^LI]: You could run multiple lab instances on the same server if you're using **[multilab](../plugins/multilab.md)** plugin.

```
$ netlab status --all
Active lab instance(s)

┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ id      ┃ directory                 ┃ status  ┃ providers ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ default │ /home/pipi/net101/tools/X │ started │ clab      │
└─────────┴───────────────────────────┴─────────┴───────────┘
```


## Cleanup a Lab Instance

The **netlab status cleanup _instance_** command shuts down the specified lab instance:

```
$ netlab status --cleanup
Cleanup will remove lab instance "default" in /home/user/net101/tools/X. Are you sure? [y/n]y
Shutting down lab default in /home/user/net101/tools/X
Read transformed lab topology from snapshot file netlab.snapshot.pickle

┌──────────────────────────────────────────────────────────────────────────────────┐
│ CHECKING virtualization provider installation                                    │
└──────────────────────────────────────────────────────────────────────────────────┘
[SUCCESS] clab installed and working correctly

┌──────────────────────────────────────────────────────────────────────────────────┐
│ STOPPING clab nodes                                                              │
└──────────────────────────────────────────────────────────────────────────────────┘
INFO[0000] Parsing & checking topology file: clab.yml
INFO[0000] Destroying lab: X
INFO[0000] Removed container: clab-X-host-2
INFO[0000] Removed container: clab-X-spine-2
INFO[0000] Removed container: clab-X-leaf-3
INFO[0000] Removed container: clab-X-spine-1
INFO[0000] Removed container: clab-X-leaf-1
INFO[0001] Removed container: clab-X-leaf-2
INFO[0001] Removed container: clab-X-host-1
INFO[0001] Removed container: clab-X-leaf-4
INFO[0001] Removing containerlab host entries from /etc/hosts file

┌──────────────────────────────────────────────────────────────────────────────────┐
│ CLEANUP configuration files                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
... removing clab.yml
... removing directory tree clab_files
... removing ansible.cfg
... removing hosts.yml
... removing directory tree group_vars
... removing directory tree host_vars
... removing netlab.snapshot.yml
... removing netlab.snapshot.pickle
```