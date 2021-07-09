# create-topology

```{warning}
**create-topology** script has been replaced with significantly simpler **‌netlab create** command in release 0.8. If you want to use the original CLI options, use the (undocumented) **netlab topology** command. 

To use the **create-topology** script, download the source code from GitHub and use `source setup.sh` to set up PATH variable.
```

The **create-topology** script reads:

* Network topology in YAML format (default: `topology.yml`)
* Optional default settings in YAML format (default: `topology-defaults.yml`)
* Global default settings (`topology-defaults.yml` in *netsim* package directory)

... and creates device- and link-level data structures fully describing network topology and IP addressing. These data structures can then be used to create:

* **Vagrantfile** supporting *[libvirt](../labs/libvirt.md)* or *[virtualbox](../labs/virtualbox.md)* environment
* **clab.yml** file used by *containerlab*.
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
  --hostvars {min,files,dirs}
                        Ansible hostvars format
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --view            Display data instead of creating a file
```

Typical uses (testing topology and inspecting results):

* `create-topology` to read and validate topology file
* `create-topology -x -v` to display expanded topology data structure
* `create-topology -p -v` to display Vagrantfile 
* `create-topology -i -v` to display Ansible inventory data structure

Typical uses (creating configuration files):

* `create-topology -p -i -c` to create everything you need to get started (**Vagrantfile**, Ansible inventory and **ansible.cfg**)
* `create-topology -p` to create **Vagrantfile**
* `create-topology -i -c` to create Ansible inventory (in **hosts.yml**), **ansible.cfg** (making inventory file the default inventory), **group_vars** and **host_vars**
* `create-topology -i --hostvars min` to dump all data structures into a single Ansible inventory file (**hosts.yml**)

For more details on topology file format, please read the [lab topology overview](../topology-overview.md) and [reference documentation](../topology-reference.md).
