(netlab-collect)=
# Collecting Device Configurations

The **netlab collect** command collects device configurations using Ansible *device facts* modules (or an equivalent list of Ansible tasks). The configurations are stored in the specified output directory (default: *config*).

A single configuration file in the output directory is created for most network devices; multiple files are collected from FRR and Cumulus VX. The configuration files have a `.cfg` suffix unless you specify a different suffix (without the leading dot) with the `--suffix` parameter.

After collecting the device configurations, you can save them in a tar archive with the `--tar` option and clean up the working directory with the `--cleanup` option.

```{tip}
* The **netlab collect** command is just a thin wrapper around an Ansible playbook which uses the Ansible inventory created by the **netlab create** or **netlab up** command.
* When executed with the `-i` option, **‌netlab collect** switches to the lab directory to execute the Ansible playbook, but stores the results within the directory from which it was executed.
```

## Usage

```text
usage: netlab collect [-h] [-v] [-q] [-o [OUTPUT]] [--suffix SUFFIX] [--tar TAR]
                      [--cleanup] [-i INSTANCE]

Collect device configurations

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -q, --quiet           Run Ansible playbook and tar with minimum output
  -o, --output [OUTPUT]
                        Output directory (default: config)
  --suffix SUFFIX       Configure file(s) suffix (default: cfg)
  --tar TAR             Create configuration tarball
  --cleanup             Clean up config directory and modified configuration file after
                        creating tarball
  -i, --instance INSTANCE
                        Specify lab instance to collect configuration from

All other arguments are passed directly to ansible-playbook
```
