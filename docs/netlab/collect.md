# Collecting Device Configurations

**netlab collect** command uses Ansible *device facts* modules (or an equivalent list of Ansible tasks) to collect device configurations and store them in specified output directory.

A single configuration file in the output directory is created for most network devices; multiple files stored in host-specific subdirectory are collected from Cumulus VX.

## Usage

```text
usage: netlab collect [-h] [-v] [-o [OUTPUT]]

Collect device configurations

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -o [OUTPUT], --output [OUTPUT]
                        Output directory (default: config)

All other arguments are passed directly to ansible-playbook
```
