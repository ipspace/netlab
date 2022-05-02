# Start Virtual Lab

**netlab up** is a high-level command that:

* Uses **[netlab create](create.md)** to create virtualization provider configuration file, transformed topology snapshot, and network automation configuration files (Ansible inventory);
* Checks the [virtualization provider](../providers.md) installation;
* Starts the virtual lab using the [selected virtualization provider](topology-reference-top-elements);
* Performs provider-specific initialization (see below)
* Deploys device configurations with **[netlab initial](initial.md)** command unless it was started with the `--no-config` flag

You can use `netlab up` to create configuration files and start the lab, or use `netlab up --snapshot` to start a previously created lab using the transformed lab topology stored in `netlab.snapshot.yml` snapshot file.

## Usage

```text
usage: netlab up [-h] [--log] [-q] [-v] [--debug] [--defaults DEFAULTS] [-d DEVICE]
                 [-p PROVIDER] [-s SETTINGS] [--no-config] [--fast-config]
                 [topology]

Create configuration files, start a virtual lab, and configure it

positional arguments:
  topology              Topology file (default: topology.yml)

optional arguments:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  --debug               Debugging (might not execute external commands)
  --defaults DEFAULTS   Local topology defaults file
  -d DEVICE, --device DEVICE
                        Default device type
  -p PROVIDER, --provider PROVIDER
                        Override virtualization provider
  -s SETTINGS, --set SETTINGS
                        Additional parameters added to topology file
  --no-config           Do not configure lab devices
  --fast-config         Use fast device configuration (Ansible strategy = free)
  --snapshot [SNAPSHOT]
                        Use netlab snapshot file created by a previous lab run
```

```{warning}
Do not use the `--fast-config` option with custom configuration templates that must be executed in specific order. See **‌[netlab initial](netlab-initial-custom)** documentation for more details.
```

## Provider-Specific Initialization

When used with *libvirt* provider, **netlab up** creates the *vagrant-libvirt* management network before starting the virtual machines, and sets the `group_fwd_mask` for all Vagrant-created Linux bridges to [enable LLDP passthrough](https://blog.ipspace.net/2020/12/linux-bridge-lldp.html).

When used with *clab* provider, **netlab up** creates Open vSwitch bridges or standard Linux bridges needed to implement multi-access networks.
