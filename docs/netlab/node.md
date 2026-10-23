(netlab-node)=
# Start, Stop, or Pause Individual Lab Nodes

The **netlab node** command starts, stops, restarts, pauses, or unpauses individual nodes in a running lab without affecting the rest of the lab.

```{warning}
* **netlab node** works only with *containerlab* nodes.
* A restarted container loses the device configuration deployed by _netlab_. **netlab node up** and **netlab node restart** therefore run **netlab initial** (or **netlab config --reload**) on the affected nodes unless you use the `--no-config` flag.
```

## Usage

```text
usage: netlab node [-h] [-v] [-q] [--dry-run] [--no-config] [-r RELOAD] [-i INSTANCE]
                   {up,down,restart,pause,unpause} node [node ...]

Start, stop, restart, pause, or unpause individual lab nodes

positional arguments:
  {up,down,restart,pause,unpause}
                        Action to execute on the selected nodes
  node                  Node(s) to act on (node names, groups, or globs; separate them with spaces or commas)

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --dry-run             Print the commands that would be executed, but do not execute them
  --no-config           Do not configure the started nodes
  -r RELOAD, --reload-config RELOAD
                        Reload saved configurations from specified directory
  -i INSTANCE, --instance INSTANCE
                        Specify the lab instance to change nodes in
```

The **netlab node** command takes these parameters:

* The action to execute:
  * **down** stops the node container (`containerlab stop`)
  * **up** starts a stopped node container and reconnects its links (`containerlab start`)
  * **restart** stops and starts the node container (`containerlab restart`)
  * **pause** freezes all processes in the node container (`docker pause`)
  * **unpause** resumes a paused node container (`docker unpause`)
* A [list of nodes](netlab-inspect-node): node names, group names, or globs, separated by spaces or commas.

Notes:

* **netlab node** reads the transformed lab topology from the `netlab.snapshot.pickle` file created by **netlab up** or **netlab create**. Unmanaged nodes are ignored.
* After starting or restarting the nodes, **netlab node** deploys the initial device configuration with **netlab initial --limit _nodes_**. Use `--no-config` to skip this step, or `--reload-config _directory_` to reload saved configurations with **netlab config --reload** instead.
* With the `--instance` flag, you can change nodes in a lab instance running in a different directory.
* **[netlab status](status.md)** displays the state of stopped and paused containers.
* Routing protocol sessions with a paused node might time out.

## Examples

```bash
$ netlab node down r1
$ netlab node up r1
$ netlab node restart r1 r2 --no-config
$ netlab node pause r1,r2
```
