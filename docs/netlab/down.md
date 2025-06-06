(netlab-down)=
# Stop a Virtual Lab

**netlab down** destroys a virtual lab created with **[netlab up](up.md)** command.

This command uses the lab topology or the snapshot file created by **netlab up** or **[netlab create](create.md)** to find the virtualization provider and executes provider-specific CLI commands to destroy the virtual lab.

## Usage

```
$ netlab down -h
usage: netlab down [-h] [-v] [--cleanup] [--dry-run] [--force] [-i INSTANCE]

Destroy the virtual lab

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (where applicable)
  --cleanup             Remove all configuration files created by netlab create
  --dry-run             Print the commands that would be executed, but do not execute
                        them
  --force               Force shutdown or cleanup (use at your own risk)
  -i INSTANCE, --instance INSTANCE
                        Specify lab instance to shut down
```

Notes:

* **netlab down** needs transformed topology data to find the virtualization provider and link (bridge) names.
* **netlab down** reads the transformed topology from `netlab.snapshot.yml` file created by **netlab up** or **netlab create**.
* With the `--instance` flag, you can shut down a lab instance running in a different directory. Use the `netlab status --all` command to display all running instances.
* Use the `--cleanup` flag to delete all Ansible-, Vagrant- or containerlab-related configuration files.
* Use the `--force` flag with the `--cleanup` flag if you want to clean up the directory even when the virtualization provider fails during the shutdown process.

## Conflict Resolution

**netlab down** command checks the _netlab_ status file (default: `~/.netlab/status.yml`) to verify that the current lab instance (default: `default`) is not running in another directory. You can decide to proceed if you want to remove _netlab_ artifacts from the current directory, but the shutdown/cleanup process might impact the lab instance running in another directory.

After a successful completion, the **netlab down** command removes the `netlab.lock` file from the current directory and all information about the lab instance from the _netlab_ status file.
