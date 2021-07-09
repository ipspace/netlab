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

## Usage

```text
usage: netlab create [-h] [--log] [-q] [-v]
  [--defaults DEFAULTS]
  [-d DEVICE] [-p PROVIDER]
  [-i INVENTORY] [-c CONFIG] [-g VAGRANTFILE]
  [--hostvars {min,files,dirs}]
  [topology]

Create provider- and automation configuration files

positional arguments:
  topology              Topology file (default: topology.yml)

optional arguments:
  -h, --help            show this help message and exit
  --defaults DEFAULTS   Local topology defaults file
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  -d DEVICE, --device DEVICE
                        Default device type
  -p PROVIDER, --provider PROVIDER
                        Override virtualization provider
  -i INVENTORY, --inventory INVENTORY
                        Automation inventory file name (default: hosts.yml)
  -c CONFIG, --config CONFIG
                        Automation configuration file (default: ansible.cfg)
  -g VAGRANTFILE        Virtualization provider configuration file name
  --hostvars {min,files,dirs}
                        Ansible hostvars format
```

For more details on topology file format, please read the [lab topology overview](../topology-overview.md) and [reference documentation](../topology-reference.md).
