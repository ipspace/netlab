(netlab-collect)=
# Collecting Device Configurations

**netlab collect** command uses Ansible *device facts* modules (or an equivalent list of Ansible tasks) to collect device configurations and store them in specified output directory.

A single configuration file in the output directory is created for most network devices; multiple files are collected from FRR and Cumulus VX.

After collecting the device configurations, you can save them in a tar archive with the `--tar` option and clean up the working directory with `--cleanup` option.

```{tip}
* **netlab collect** command is just a thin wrapper around an Ansible playbook which uses Ansible inventory created by **netlab create** or **netlab up** command.
* When executed with the `-i` option, **‌netlab collect** switches to the lab directory to execute the Ansible playbook, but stores the results within the directory from which it was executed.
```

## Usage

```text
usage: netlab collect [-h] [-v] [-q] [-o [OUTPUT]] [--tar TAR] [--cleanup] [-i INSTANCE]

Collect device configurations

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -q, --quiet           Run Ansible playbook and tar with minimum output
  -o [OUTPUT], --output [OUTPUT]
                        Output directory (default: config)
  --tar TAR             Create configuration tarball
  --cleanup             Clean up config directory and modified configuration file after
                        creating tarball
  -i INSTANCE, --instance INSTANCE
                        Specify lab instance to collect configuration from

All other arguments are passed directly to ansible-playbook
```
