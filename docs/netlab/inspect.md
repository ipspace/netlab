# Inspect Data Structures in Transformed Lab Topology

**netlab inspect** prints data structures in transformed lab topology (usually stored in `netlab.snapshot.yml`) created by **netlab create** command. You can display data in YAML or JSON format, and select a subset of data from the transformed topology or from an individual node.

When selecting data from an individual node, _netlab_ adds group variables to node data, effectively displaying what you would see in the Ansible inventory.

```{note}
**netlab inspect** command is replicating the functionality of **netlab create -o yaml:_expression_** command with a more convenient user interface. 
```

## Usage

```text
usage: netlab inspect [-h] [--snapshot [SNAPSHOT]] [--node NODE] 
                      [--format {yaml,json}] [expr]

Inspect data structures in transformed lab topology

positional arguments:
  expr                  Data selection expression

options:
  -h, --help            show this help message and exit
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  --node NODE           Display data for selected node(s)
  --format {yaml,json}  Select data presentation format
```

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

## Node Inspection Examples

You can use the `--node` parameter to inspect the data structure of a single node, a list of nodes (separated by commas), or a wildcard expression.

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| data for node `r1`             | `netlab inspect --node r1` |
| interface data for node `r1`   | `netlab inspect --node r1 interfaces` |
| first interface on node `r1`   |  `netlab inspect --node r1 'interfaces[0]'` |
| BGP parameters on R1 and R2    | `netlab inspect --node r1,r2 bgp` |
| VRFs on all nodes              | `netlab inspect --node '*' vrfs` |

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
