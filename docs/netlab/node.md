(netlab-node)=
# Start, Stop, or Pause Individual Lab Nodes

The **netlab node** command starts, stops, restarts, pauses, or unpauses individual nodes in a running lab without affecting the rest of the lab.

```{warning}
* **netlab node** works only with *containerlab* nodes.
* A restarted container loses the device configuration deployed by _netlab_. Use **netlab initial --limit _node_** to configure it again.
```

## Usage

```text
usage: netlab node [-h] [-v] [-q] [--dry-run] [-i INSTANCE] node {up,down,restart,pause,unpause}

Start, stop, restart, pause, or unpause individual lab nodes

positional arguments:
  node                  Node(s) to act on (node names, groups, or globs, separated by commas)
  {up,down,restart,pause,unpause}
                        Action to execute on the selected nodes

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --dry-run             Print the commands that would be executed, but do not execute them
  -i INSTANCE, --instance INSTANCE
                        Specify the lab instance to change nodes in
```

The **netlab node** command takes two parameters:

* A [list of nodes](netlab-inspect-node): node names, group names, or globs, separated by commas.
* The action to execute:
  * **down** stops the node container (`containerlab stop`)
  * **up** starts a stopped node container and reconnects its links (`containerlab start`)
  * **restart** stops and starts the node container (`containerlab restart`)
  * **pause** freezes all processes in the node container (`docker pause`)
  * **unpause** resumes a paused node container (`docker unpause`)

Notes:

* **netlab node** reads the transformed lab topology from the `netlab.snapshot.pickle` file created by **netlab up** or **netlab create**.
* With the `--instance` flag, you can change nodes in a lab instance running in a different directory.
* **[netlab status](status.md)** displays the state of stopped and paused containers.
* Some devices reload their saved configuration (for example, FRR after **write memory**) when restarted, but that does not restore VLANs, VRFs, LAGs, or VXLAN.
* Routing protocol sessions with a paused node might time out.

## Examples

```bash
$ netlab node r1 down
$ netlab node r1 up
$ netlab initial --limit r1
$ netlab node r1,r2 pause
```
