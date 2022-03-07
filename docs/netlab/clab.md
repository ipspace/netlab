# Containerlab Utilities

**netlab clab** performs these *containerlab*-related functions:

* **tarball** -- creates a tar archive that can be used to recreate the lab in a vanilla *containerlab* environment without *netsim-tools*.

## netlab clab tarball

The **netlab clab tarball** command requires a running *containerlab* lab and *clab.yml* configuration file in current directory to:

* Collect device configurations
* Create a new copy of *containerlab* configuration file (*clab.config.yml*) that contains pointers to startup configurations
* Create a tar archive containing *clab.config.yml* and related device configurations.

You can use the tar archive created by **netlab clab tarball** to recreate the lab in a *containerlab* environment without *netsim-tools*.

```
usage: netlab clab tarball [-h] [-v] [-q] [--config [OUTPUT]] [--cleanup] tarball

Create a ready-to-use tarball containing containerlab configuration file and startup
configs

positional arguments:
  tarball            Destination tarball (.tar.gz will be added if needed)

optional arguments:
  -h, --help         show this help message and exit
  -v, --verbose      Verbose logging
  -q, --quiet        Run Ansible playbook and tar with minimum output
  --config [OUTPUT]  Startup configuration directory (default: config)
  --cleanup          Clean up config directory and modified configuration file after
                     creating tarball
```
