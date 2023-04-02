# Display Running Lab Instances

**netlab status** command displays the running lab instances and the provider-specific workloads (*[libvirt](../labs/libvirt.md)* virtual machines or *[containerlab](../labs/clab.md)* containers).

This command uses the *netlab* status file (default: `~/.netlab/status.yml`) to get the state of running lab instances. The status file is updated by **netlab up** and **netlab down** commands.

## Usage

```
usage: netlab status [-h] [--all] [-v] {list,show,cleanup,reset} [instance ...]

Display lab status

positional arguments:
  {list,show,cleanup,reset}
                        Lab status action
  instance              Display or cleanup specific lab instance(s)

options:
  -h, --help            show this help message and exit
  --all                 Display or cleanup all lab instance(s)
  -v, --verbose         Verbose printout(s)
```

* **netlab status** or **netlab status list** displays the currently-running lab instances.
* **netlab status show** displays detailed state (including state change log) of selected lab instance(s)
* **netlab status cleanup** shuts down selected lab instance(s). It changes the current directory to the lab directory saved in the status file and executes **netlab down --cleanup** in that directory
* **netlab status reset** deletes the status file. Use this command only if the status file becomes corrupted.

## Running Lab Instances

The **netlab status list** command displays all running lab instances[^LI], their working directories, and the virtual machines (domains) and containers running on the current server.

[^LI]: You could run multiple lab instances on the same server if you're using **[multilab](../plugins/multilab.md)** plugin.

```
$ netlab status
Lab default in /home/user/net101/tools/X
  status: started
  provider(s): clab

Running containers
================================================================================
CONTAINER ID   IMAGE                COMMAND        CREATED          STATUS          PORTS     NAMES
20878d36c187   networkop/cx:4.4.0   "/sbin/init"   19 seconds ago   Up 18 seconds             clab-ospfv2-r1
799cf6091c03   networkop/cx:4.4.0   "/sbin/init"   19 seconds ago   Up 18 seconds             clab-ospfv2-r2


KVM/libvirt domains (virtual machines)
================================================================================
 Id   Name   State
--------------------
```

## Display Lab Instance State

The **netlab status show** command displays more details about selected lab instance(s), including the state change log:

```
Lab default in /home/user/net101/tools/X
  status: started
  provider(s): clab

Log:
================================================================================
2023-03-29T10:28:22.609058+02:00: starting lab
2023-03-29T10:28:22.610693+02:00: starting provider clab
2023-03-29T10:28:25.188872+02:00: clab workload started
2023-03-29T10:28:25.194336+02:00: deploying initial configuration
2023-03-29T10:28:25.681063+02:00: deploying configuration: complete configuration
2023-03-29T10:28:36.042937+02:00: configuration deployment complete
2023-03-29T10:28:36.059921+02:00: initial configuration complete
2023-03-29T10:28:36.062101+02:00: started
```

## Cleanup a Lab Instance

The **netlab status cleanup _instance_** command shuts down the specified lab instance:

```
$ netlab status cleanup default
Cleanup will remove all specified lab instances. Are you sure? [Y/n]y
Shutting down lab default in /home/user/net101/tools/X
Reading transformed lab topology from snapshot file netlab.snapshot.yml

Step 2: Checking virtualization provider installation
============================================================
.. all tests succeeded, moving on


Step 2: stopping the lab
============================================================
INFO[0000] Parsing & checking topology file: clab.yml
INFO[0000] Destroying lab: ospfv2
INFO[0000] Removed container: clab-ospfv2-r2
INFO[0000] Removed container: clab-ospfv2-r1
INFO[0000] Removing containerlab host entries from /etc/hosts file

Step 3: Cleanup configuration files
============================================================
... removing clab.yml
... removing ansible.cfg
... removing hosts.yml
... removing directory tree group_vars
... removing directory tree host_vars
... removing netlab.snapshot.yml
```