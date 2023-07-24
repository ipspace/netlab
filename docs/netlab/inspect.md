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
  --node NODE           Display data for selected node
  --format {yaml,json}  Select data presentation format
```

## Examples

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| whole transformed topology     | `netlab inspect`    |
| node data                      | `netlab inspect nodes` |
| address pools                  | `netlab inspect addressing`  |
| data for node `r1`             | `netlab inspect --node r1` |

Formatting modifier can select any subset of the lab topology, for example:

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| interface data for node `r1`   | `netlab inspect --node r1 interfaces` |
| device data for device `eos` | `netlab inspect defaults.devices.eos` |
| valid attributes for the BGP module | `netlab inspect defaults.bgp.attributes` |

Finally, the formatting modifier is evaluated as a Python expression, so you can display most things that can be expressed as a one-line expression (don't forget to quote the expression):

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| second interface on node `r1`  |  `netlab inspect --node r1 'interfaces[1]'` |
| node names                     | `netlab inspect 'list(nodes.keys())'` |
