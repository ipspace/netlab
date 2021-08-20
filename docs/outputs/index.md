# Output Formats

**netlab create** command can call one or more output modules to create files that can be used with Vagrant, Ansible, containerlab, or graphviz. The output modules are specified with one or more `-o` parameters. When no `-o` parameter is specific, **netlab create** calls *provider* and *ansible* output modules.

Each `-o` parameter specifies an output module, formatting modifiers, and output filename in the **format:modifiers=file(s)** format:

* **format** is the desired output module. It can be one of *provider*, *ansible*, *graph*, *yaml* or *json*.
* Some output modules use optional formatting modifiers -- you can specify Ansible inventory format, graph type, or parts of the transformed data structure that you want to see in YAML or JSON format
* All output formats support optional destination file name. Default file name is either hard-coded in the module or specified in **defaults.outputs** part of lab topology.

The following output modules are included in **netsim-tools** distribution; you can create your own by adding modules to `netsim/outputs` directory:

```eval_rst
.. toctree::
   :maxdepth: 1

   provider.md
   ansible.md
   graph.md
   yaml-or-json.md
```
