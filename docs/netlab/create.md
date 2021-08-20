# Create Lab Configuration Files

The **netlab create** command reads network topology description in YAML format, performs data transformation from high-level data model to devices-and-links data model, and creates virtualization- and automation configuration files needed to set up your lab.

## Network Topology Sources

**netlab create** uses these sources of information to build the desired lab topology:

* Network topology in YAML format (default: `topology.yml`)
* Optional default settings in YAML format (default: `topology-defaults.yml`)
* Global default settings (`topology-defaults.yml` in *netsim* package directory)

## Creating Configuration Files

After reading the network topology, **netlab create** performs a complex data transformation to create device- and link-level data structures fully describing network topology, IP addressing and (optional) routing protocols. These data structures are then used to create:

* **Vagrantfile** supporting *[libvirt](../labs/libvirt.md)* or *[virtualbox](../labs/virtualbox.md)* environment
* **clab.yml** file used by *containerlab*.
* Ansible inventory, either as a single-file data structure, or as a minimal inventory file with data stored primarily in **host_vars** and **group_vars**
* YAML or JSON representation of transformed lab topology
* Various graphs in *graphviz* DOT format

## Usage

```text
usage: netlab create [-h] [--log] [-q] [-v] [--defaults DEFAULTS] [-d DEVICE]
                     [-p PROVIDER] [-s SETTINGS] [-o OUTPUT]
                     [topology]

Create provider- and automation configuration files

positional arguments:
  topology              Topology file (default: topology.yml)

optional arguments:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  --defaults DEFAULTS   Local topology defaults file
  -d DEVICE, --device DEVICE
                        Default device type
  -p PROVIDER, --provider PROVIDER
                        Override virtualization provider
  -s SETTINGS, --set SETTINGS
                        Additional parameters added to topology file
  -o OUTPUT, --output OUTPUT
                        Output format(s): format:option=filename

output files created when no output is specified:

  * Virtualization provider file with provider-specific filename
    (Vagrantfile or clab.yml)
  * Ansible inventory file (hosts.yml) and configuration (ansible.cfg)

For a complete list of output formats please consult the documentation
```

For more details on topology file format, please read the [lab topology overview](../topology-overview.md) and [reference documentation](../topology-reference.md).

## Output Formats

Without specifying the output format(s), **netlab create** creates a provider configuration file (*Vagrantfile* or *clab.yml*) and Ansible inventory data (*hosts.yml*, *ansible.cfg*, *host_vars*, *group_vars*).

You could specify one or more output formats with the `-o` CLI parameter. For more details please read the [output formats](../outputs/index.md) part of the documentation.

## Setting Topology Parameters from Command Line

The following CLI flags can be used to change individual topology parameters:

* `-d` sets default device type (**defaults.device**)
* `-p` sets virtualization provider (**provider**)
* `-s` uses `key=value` format to set specified topology element  value. The key could be a hierarchical dotted name.

### Example

Assume the following topology file that uses *containerlab* provider to set up a lab of three Cumulus VX devices:

```
defaults:
  device: cumulus

provider: clab

module: [ ospf ]
nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3 ]
```

When running...

```
$ netlab create -d iosv -p libvirt -s ospf.area=123
```

... you'll get a Vagrant file using *vagrant-libvirt* plugin that will create a lab with three Cisco IOS routers. OSPF configuration of those routers will use area 123.
