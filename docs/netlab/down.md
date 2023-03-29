# Stop Virtual Lab

**netlab down** destroys a virtual lab created with **[netlab up](up.md)** command.

This command uses the lab topology or the snapshot file created by **netlab up** or **[netlab create](create.md)** to find the virtualization provider, and executes provider-specific CLI commands to destroy the virtual lab.

## Usage

```
usage: netlab down [-h] [--defaults DEFAULTS] [-d DEVICE] [-p PROVIDER] [-s SETTINGS]
                   [-v] [--cleanup] [--snapshot SNAPSHOT]
                   [topology]

Destroy the virtual lab

positional arguments:
  topology              Topology file (default: topology.yml)

optional arguments:
  -h, --help            show this help message and exit
  --defaults DEFAULTS   Local topology defaults file
  -d DEVICE, --device DEVICE
                        Default device type
  -p PROVIDER, --provider PROVIDER
                        Override virtualization provider
  -s SETTINGS, --set SETTINGS
                        Additional parameters added to topology file
  -v, --verbose         Verbose logging (where applicable)
  --cleanup             Remove all configuration files created by netlab create
  --snapshot SNAPSHOT   Transformed topology snapshot file
```

Notes:

* **netlab down** needs transformed topology data to find the virtualization provider and link (bridge) names.
* **netlab down** reads the transformed topology from `netlab.snapshot.yml` file created by **netlab up** or **netlab create** unless you specify the topology file name or any of the `-d`, `-p` or `-s` flags.
* Use the `--cleanup` flag to delete all Ansible-, Vagrant- or containerlab-related configuration files.

## Conflict Resolution

**netlab down** command checks the _netlab_ status file (default: `~/.netlab/status.yml`) to verify that the current lab instance (default: `default`) is not running in another directory. You can decide to proceed if you want to remove _netlab_ artifacts from the current directory, but the shutdown/cleanup process might impact the lab instance running in another directory.

After a successful completion, **netlab down** command removes the `netlab.lock` file from the current directory, and all information about the lab instance from the _netlab_ status file.
