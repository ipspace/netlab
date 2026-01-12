(output-formats)=
# Output Formats

The **netlab create** command (also invoked by the **netlab up** command) can call one or more output modules to create files that can be used with Vagrant, Ansible, containerlab, graphviz, D2, or *graphite* tools. The output modules are specified with one or more `-o` parameters. When no `-o` parameter is specified, **netlab create** calls all modules specified in the **‌defaults.netlab.create.output** [topology default](topo-defaults).

Each `-o` parameter specifies an output module, formatting modifiers, and output filename in the **module:modifiers=file(s)** format:

* **module** is the desired output module. It can be one of *ansible*, *config*, *graph*, *json*, *pickle*, *provider*, *report*, *tools*, or *yaml*.

```{tip}
* The **‌netlab show outputs** command displays the available output modules.
* Use the *‌none* output module when you want to test the lab topology transformation without generating any outputs.
```

* Some output modules use optional formatting modifiers -- you can specify Ansible inventory format, graph type, or parts of the transformed data structure that you want to see in YAML or JSON format
* Most output formats support an optional destination file name. The default file name is either hard-coded in the module or specified in **defaults.outputs** part of lab topology.

The following output modules are included in the **netlab** distribution; you can create your own by adding modules to the `netsim/outputs` directory. Use **[netlab show outputs](netlab-show-outputs)** to display the up-to-date list of the output modules.

```eval_rst
.. toctree::
   :maxdepth: 1

   ansible.md
   d2.md
   devices.md
   graph.md
   provider.md
   report.md
   yaml-or-json.md
```
