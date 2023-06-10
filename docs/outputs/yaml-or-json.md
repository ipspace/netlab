# YAML and JSON Output Modules

*yaml* and *json* output modules display transformed lab topology in YAML or JSON format. You can invoke them by specifying `-o yaml` or `-o json` parameter in **netlab create** command.

Both output modules can take an optional destination file name (default: stdout).

Multiple formatting modifiers (separated with colons) can be used to reduce the amount of information displayed from the transformed lab topology:

* **nodefault** -- Remove default settings (**defaults** key).
* **noaddr** -- Remove address pools (**addressing** key).
* Any other formatting modifier is evaluated as a Python expression within the transformed lab topology context.

**Examples:**

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| whole transformed topology     | `netlab create -o yaml` |
| whole topology without the defaults | `netlab create -o yaml:nodefault` |
| whole topology without the defaults or addressing pools | `netlab create -o yaml:nodefault:noaddr` |
| node data                      | `netlab create -o yaml:nodes`  |
| address pools                  | `netlab create -o yaml:addressing`  |

Formatting modifier can select any subset of the lab topology, for example:

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| data for node `r1`             | `netlab create -o yaml:nodes.r1` |
| interface data for node `r1`   | `netlab create -o yaml:nodes.r1.interfaces` |
| device data for device `eos` | `netlab create -o yaml:defaults.devices.eos` |
| settings for D2 output module | `netlab create -o yaml:defaults.outputs.d2` |
| valid attributes for the BGP module | `netlab create -o yaml:defaults.bgp.attributes` |

Finally, the formatting modifier is evaluated as a Python expression, so you can display anything that can be expressed as a one-line expression (you will probably have to quote the whole `yaml:expression` string):

| To display this information... | ...use this command |
|--------------------------------|---------------------|
| second interface on node `r1`  |  `netlab create -o 'yaml:nodes.r1.interfaces[1]'` |
| node names                     | `netlab create -o 'yaml:list(nodes.keys())'` |

**netlab create** command stores the results into an output file when you specify `format=output` or `format:expr=output` value for the `--output` parameter. For example:

| To write this information into a file ... | ... use this command |
|--------------------------------|---------------------|
| whole topology into `transformed.yaml` | `netlab create -o yaml=transformed.yaml` |
| node data into `nodes.yaml`    | `netlab create -o yaml:nodes=nodes.yaml` |
| link data into `links.json`    | `netlab create -o json:links=links.json` |
