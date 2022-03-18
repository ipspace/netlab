# Start Virtual Lab

**netlab up** is a high-level command that uses other **netlab** commands to:

* Create virtualization provider configuration files and transformed topology snapshot;
* Create network automation configuration files;
* Check the virtualization provider installation;
* Start the virtual lab;
* Deploy device configurations with **[netlab initial](initial.md)** command unless it was started with the `--no-config` flag

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
```

```{warning}
Do not use the `--fast-config` option with configuration modules that depend on other configuration modules (example: MPLS, SR). See **‌[netlab initial](netlab-initial-module)** documentation for more details.
```

## Provider-Specific Initialization

When used with *libvirt* provider, **netlab up** creates the *vagrant-libvirt* management network before starting the virtual machines, and sets the `group_fwd_mask` for all Vagrant-created Linux bridges to [enable LLDP passthrough](https://blog.ipspace.net/2020/12/linux-bridge-lldp.html).

When used with *clab* provider, **netlab up** creates Open vSwitch bridges or standard Linux bridges needed to implement multi-access networks.
