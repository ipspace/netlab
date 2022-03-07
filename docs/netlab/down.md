# Stop Virtual Lab

**netlab down** destroys a virtual lab created with **[netlab up](up.md)** command.

This command uses provider-specific CLI commands to destroy the virtual lab, and needs the lab topology file to discover the virtualization provider the lab is using.

## Usage

```
usage: netlab down [-h] [--defaults DEFAULTS] [-d DEVICE] [-p PROVIDER] [-s SETTINGS]
                   [-v] [--cleanup]
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
```

Notes:

* If you changed the virtualization provider with `-p` flag in **netlab create** or **netlab up**, you MUST specify the same value in **netlab down**
* Use the `--cleanup` flag to delete all Ansible-, Vagrant- or containerlab-related configuration files.
