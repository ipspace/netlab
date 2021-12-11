# Deploying Initial Device Configurations

**netlab initial** command uses a set of device-specific Jinja2 templates and an internal Ansible playbook to deploy initial device configurations created from expanded inventory data created with **[netlab create](create.md)** command.

The playbook deploys device configurations in two steps:

* Initial device configurations[^1]
* Module-specific device configurations[^2]

[^1]: Controlled by `-i` flag or **initial** Ansible tag
[^2]: Controlled by `-m` flag or **module** Ansible tag

When run with **-v** parameter, the command displays device configurations before deploying them.

## Usage

```text
usage: netlab initial [-h] [--log] [-q] [-v] [-i] [-m [MODULE]] [-o [OUTPUT]]

Initial device configurations

optional arguments:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  -i, --initial         Deploy just the initial configuration
  -m [MODULE], --module [MODULE]
                        Deploy module-specific configuration (optionally including a 
                        list of modules separated by commas)
  -o [OUTPUT], --output [OUTPUT]
                        Create a directory with initial configurations instead of
                        deploying them

All other arguments are passed directly to ansible-playbook
```

## Initial Device Configurations

Initial device configurations are created from inventory data and templates in `netsim/ansible/templates/initial` directory. Device-specific configuration template is selected using `ansible_network_os` value (making IOSv and CSR 1000v templates identical).

The following initial configuration parameters are supported:

* hostname
* interface IPv4 and IPv6 addresses
* unnumbered interfaces
* interface descriptions
* interface MAC addresses
* interface bandwidth (when supported by the device)

The initial configuration also includes LLDP running on all interfaces apart from the management interface (not configurable).

Default passwords and other default configuration parameters are supposed to be provided by the Vagrant boxes.

## Module Configurations

Module-specific device configurations are created from templates in `netsim/ansible/templates/_module_` directory. Device-specific configuration template is selected using `ansible_network_os` value. See the [module descriptions](../module-reference.md) for list of supported model parameters.

## Limiting the Scope of Configuration Deployments

Without specifying `-i` or `-m` flag, the command deploys all initial configurations. To control the deployment of initial configurations:

* use the `-i` flag to deploy initial device configurations. 
* use the `-m` flag to deploy module-specific configurations. 
* use the `-m` flag followed by a module name (example: `-m ospf -m bgp`) to deploy device configuration for specific modules. You can use the `-m` flag multiple times.

All unrecognized parameters are passed to internal `initial-config.ansible` Ansible playbook. You can use **ansible-playbook** CLI parameters to modify the configuration deployment, for example:

* `-l` parameter to deploy device configurations on a subset of devices.
* `-C` parameter to run the Ansible playbook in dry-run mode. Combine it with `-v` parameter to see the configuration changes that would be deployed[^3]

[^3]: The Ansible playbook uses **vtysh** on Cumulus VX to deploy the FRR-related configuration changes from a file. The dry run will not display the configuration changes.

## Debugging Initial Configurations

* Use `-o` flag to create device configurations without deploying them. The optional value of `-o` parameter specifies the output directory name (default: `config`)
* To display device configurations from within the Ansible playbook without deploying them, use `-v --tags test` flags (a bogus playbook tag disables configuration deployment).
