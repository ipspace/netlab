# Create Network Topology

This script creates a device-level and link-level data structures describing desired network topology. These data structures are then used to create **Vagrantfile** to create the desired topology and Ansible inventory describing the topology.

## Usage

The **create-topology** script reads:

* Network topology in YAML format (default: `topology.yml`)
* Optional default settings in YAML format (default: `topology-defaults.yml`)
* Global default settings (`topology-defaults.yml` in script directory)

... and creates device- and link-level data structures fully describing network topology and IP addressing. These data structures can then be used to create:

* **Vagrantfile** supporting **libvirt** environment
* Ansible inventory, either as a single-file data structure, or as a minimal inventory file with data stored primarily in **host_vars** and **group_vars**
* YAML file with expanded topology data (in case you need it for further automation tasks)

```
usage: create-topology ...

Create topology data from topology description

optional arguments:
  -h, --help            show this help message and exit
  -t TOPOLOGY, --topology TOPOLOGY
                        Topology file
  --defaults DEFAULTS   Local topology defaults file
  -x [XPAND], --expanded [XPAND]
                        Create expanded topology file
  -g [VAGRANT], --vagrantfile [VAGRANT]
                        Create Vagrantfile
  -i [INVENTORY], --inventory [INVENTORY]
                        Create Ansible inventory file, default hosts.yml
  -c [CONFIG], --config [CONFIG]
                        Create Ansible configuration file, default ansible.cfg
  --hostvars [HOSTVARS]
                        Create Ansible hostvars
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --view            Display data instead of creating a file
```

Typical uses:

* **create-topology** to read and validate topology file
* **create-topology -x -v** to display expanded topology data structure
* **create-topology -g -v** to display Vagrantfile and **create-topology -g** to create Vagrantfile
* **create-topology -i -v** to display Ansible inventory data structure, and **create-topology -i --hostvars** to create Ansible inventory (in **hosts.yml**), **group_vars** and **host_vars**

## Topology Format

Topology description file is a YAML file with three elements:

* **defaults** - describing topology-wide defaults like default device type
* **addressing** - [IPv4 and IPv6 pools](addressing.md) used to address management, loopback, LAN, P2P and stub interfaces
* **nodes** - [list of nodes](nodes.md)
* **links** - [list of links](links.md)

Optionally, you can use the fourth element (**name**) to give the topology a name. That name (default: directory name) will be used when creating Vagrant virtual networks.

### Nodes

Topology files should include a *list of nodes*. Individual nodes could be specified by node *name* (string) or a dictionary of node attributes including **name**. Use a node dictionary when you want to specify non-default device type or additional node attributes.

Example:
```
nodes:
- node: pe1
  as: 65000
  bgp: [ pe2 ]
  device: csr
- p1
- p2
- node: pe2
  as: 65000
  bgp: [ pe1 ]
```

**Notes:** 
* For more details read the [nodes](nodes.md) part of [lab topology reference](topology-reference.md)
* Additional attributes specified in a node dictionary are copied directly into Ansible inventory.

### Links

The second element of network topology are *links* between nodes. Links can be specified as:

* A dictionary of nodes. Use this format when you want to have a tight control over interface attributes like IP addresses
* A list of nodes. Use this format for multi-access interface when you're OK with default IP addressing.
* A string in *node*-*node* format. Use this format for a point-to-point link.

Example:
```
links:
- pe1-p1
- [ pe1, p2 ]
- description: Primary uplink between PE2 and P1
	prefix: 10.0.2.0/24
	bridge: PVLAN
	pe2:
	  ip: 10.0.2.17/24
  p1:
    ip: 10.0.2.18/24
- pe2-p2
```

### Defaults

You can specify these topology-wide defaults. Most default values must be specified somewhere (the **create-topology** script expects to get them):

* In **default** element of the topology file
* In **topology-defaults.yml** file in the same directory as the topology file
* In global **topology-defaults.yml** file.

**device**
: Default device type. Used unless you specified **device** element in node dictionary.

**addressing**
: Default address pools see [addressing](addressing.md) for more details.
