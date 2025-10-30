(netlab-inspect)=
# Inspect Data Structures in Transformed Lab Topology

**netlab inspect** prints data structures in a transformed lab topology ([more details](netlab-inspect-data-source)). You can display data in YAML or JSON format and select a subset of data from the transformed topology or an individual node.

When selecting data from an individual node, _netlab_ adds group variables to node data, effectively displaying what you would see in the Ansible inventory.

```{note}
The **netlab inspect** command is replicating the functionality of the **netlab create -o yaml:_expression_** command with a more convenient user interface. 
```

## Usage

```text
usage: netlab inspect [-h] [--node NODE] [--all] [--format {yaml,json}] [-q]
                      [-i INSTANCE] [--snapshot [SNAPSHOT]] [-t TOPOLOGY]
                      [expr]

Inspect data structures in a lab topology

positional arguments:
  expr                  Data selection expression

options:
  -h, --help            show this help message and exit
  --node NODE           Display data for selected node(s)
  --all                 Add global Ansible variables to node data
  --format {yaml,json}  Select data presentation format
  -q, --quiet           Report only major errors
  -i, --instance INSTANCE
                        Specify lab instance to inspect
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  -t, --topology TOPOLOGY
                        Topology file or URL
```

(netlab-inspect-data-source)=
The **netlab inspect** command gets its data from:

* The topology file specified with the `-t` argument
* The lab instance specified with the `-i` argument
* The snapshot file specified with the `--snapshot` argument
* The default snapshot file (`netlab.snapshot.pickle`)
* The default lab topology file (`topology.yml`)

The `netlab.snapshot.pickle` snapshot file is created when a lab is started and deleted when you shut down the lab with the `netlab down --cleanup` command.

## Topology Inspection Examples

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| whole transformed topology     | `netlab inspect`    |
| node data                      | `netlab inspect nodes` |
| address pools                  | `netlab inspect addressing`  |

You can inspect any subset of the lab topology, for example:

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| device data for device `eos` | `netlab inspect defaults.devices.eos` |
| valid attributes for the BGP module | `netlab inspect defaults.bgp.attributes` |

Finally, the data selection argument is evaluated as a Python expression, so you can display most things that can be expressed as a one-line expression (don't forget to quote the expression):

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| node names                     | `netlab inspect 'list(nodes.keys())'` |

(netlab-inspect-node)=
## Node Inspection Examples

You can use the `--node` parameter to inspect the data structure of a single node, a group of nodes (where `all` is equivalent to `*`), all nodes running the specified device type, or all nodes matching a wildcard (glob) expression. You can also specify multiple parameters separated by commas.

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| data for node `r1`             | `netlab inspect --node r1` |
| interface data for node `r1`   | `netlab inspect --node r1 interfaces` |
| first interface on node `r1`   |  `netlab inspect --node r1 'interfaces[0]'` |
| BGP parameters on R1 and R2    | `netlab inspect --node r1,r2 bgp` |
| BGP parameters of routers in group as65101 | `netlab inspect --node as65101 bgp` |
| BGP parameters of FRR devices  | `netlab inspect --node frr bgp` |
| BGP parameters of IOL and EOS devices | `netlab inspect --node iol,eos bgp` |
| VRFs on all nodes              | `netlab inspect --node '*' vrfs` |
| VRFs on all nodes (alternate)  | `netlab inspect --node all vrfs` |
| VLANs on all nodes start with 'r' | `netlab inspect --node 'r*' vlans` |

```{warning}
You can use Python expressions only when specifying a single node to inspect.
```

Node data includes Ansible group variables, for example:

```
$ netlab inspect --node r1
af:
  ipv4: true
ansible_connection: network_cli
ansible_host: 192.168.121.101
ansible_network_os: eos
ansible_ssh_pass: vagrant
ansible_user: vagrant
box: arista/veos
...
```

```{tip}
Use the `--all` option if you want to display the global variables available in Ansible playbooks (address pools, paths, named prefixes)
```

Data from multiple nodes is shown in a tabular format, for example:

```
$ netlab inspect --node r1,r2 loopback
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ r1                      ┃ r2                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ifindex: 0              │ ifindex: 0              │
│ ifname: Loopback0       │ ifname: Loopback0       │
│ ipv4: 10.0.0.1/32       │ ipv4: 10.0.0.2/32       │
│ neighbors: []           │ neighbors: []           │
│ type: loopback          │ type: loopback          │
│ virtual_interface: true │ virtual_interface: true │
└─────────────────────────┴─────────────────────────┘
```
