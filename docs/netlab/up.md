# Start Virtual Lab

**netlab up** is a high-level command that uses other **netlab** commands to:

* Create virtualization provider configuration files;
* Create network automation configuration files;
* Check the virtualization provider installation;
* Start the virtual lab;
* Deploy initial device configurations with **[netlab initial](initial.md)** command.
* Deploys [group-specific configuration templates](../groups.md#custom-configuration-templates) with **[netlab config](config.md)** command.

## Usage

```text
usage: netlab up [-h] [--log] [-q] [-v] [--debug] [--defaults DEFAULTS] [-d DEVICE]
                 [-p PROVIDER] [-s SETTINGS]
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
```

## Provider-Specific Initialization

When used with *libvirt* provider, **netlab up** changes the `group_fwd_mask` for all Vagrant-created Linux bridges to [enable LLDP passthrough](https://blog.ipspace.net/2020/12/linux-bridge-lldp.html).

## Group-Specific Configuration Templates

After executing **[netlab initial](initial.md)** command, **netlab up** executes **[netlab config](config.md) *template* \--limit *group*** command for every [group](../groups.md) with **config** attribute, .

If a **config** attribute contains a list of templates, the templates are deployed in the sequence specified in the **config** attribute.
