(plugin-files)=
# Embed Files and Configuration Templates in Lab Topology

The **files** plugin allows you to include small files and custom configuration templates directly in the lab topology, enabling the deployment of a complete solution as a single lab topology file.

The plugin defines two new topology attributes:

* **files** -- a dictionary or list of extra files to create in the lab directory
* **configlets** -- a dictionary of custom configuration templates

It also extends the meaning of the node/group **config** attribute and adds the **config.inline** attribute to validation tests.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(plugin-files-create)=
## Creating Extra Files

The **files** attribute can be a list of file paths and their contents. Every element of the list has to have two attributes:

* **path**: The file path relative to the lab directory
* **content**: File content

Example:

```
plugin: [ files ]

files:
- path: README.md
  content: |
    The README.md file
```

```{tip}
Always use the YAML *literal ‌block scalar header* (`|`) for the file content; otherwise, the whole content will be folded into a single line.
```

The **files** attribute can also be specified as a dictionary of  file paths and content, for example:

```
plugin: [ files ]

files:
  hey/README.md: |
    The README.md file
```

```{tip}
The **files** dictionary is converted to a list of files before the lab topology transformation. If you want to use the contents of this attribute in plugins or custom templates/reports, use the list format.
```

The files specified in the **files** attribute are created just before the output modules are called from the **netlab create** command (also used in **netlab up**). They are automatically removed by the **netlab down --cleanup** command.

```{warning}
* The plugin will overwrite the existing files.
* The files specified in the **‌files** list will be removed during the `netlab down --cleanup` process, even when they existed before the `netlab up` was executed.
```

## Creating Custom Configuration Templates

The **configlets** dictionary can be used to create custom configuration templates. Its contents are automatically converted to [elements of the **files** list](plugin-files-create), but provide a more intuitive way of specifying the templates.

For example, the following **configlets** dictionary creates **ifup.j2** and **ifdown.j2** custom configuration templates in the lab directory:

```
configlets:
  ifup: |
    ip link set eth1 up
  ifdown: |
    ip link set eth1 down
```

```{tip}
Always use the YAML *literal ‌block scalar header* (`|`) for the configlet content; otherwise, the whole content will be folded into a single line.
```

You can use a more structured **configlets** dictionary to create custom configuration templates for multiple nodes, devices, or providers. For example, the following dictionary creates **ifup/eos.j2** and **ifup/frr.j2** files that can then be used as `ifup` custom configuration templates on Arista EOS or FRR:

```
configlets:
  ifup:
    eos: |
      interface Ethernet1
        no shutdown
    frr: |
      ip link set eth1 up
```

The **configlets** dictionary structure can be recursive, creating more specific configuration templates. For example, the following dictionary results in **ifup/r1.eos.j2**, **ifup/r1.frr.j2** and **ifup/r2.j2** files:

```
configlets:
  ifup:
    r1:
      eos: |
        interface Ethernet1
          no shutdown
      frr: |
        ip link set eth1 up
    r2: |
      ip link set eth2 up
```

```{tip}
Due to the structure of the custom configuration filenames, the **‌files** plugin prepends `-` to provider names. All other filename components are separated by dots.

Use the **netlab show defaults paths.custom.files** command to display the order of components _netlab_ expects you to use in the custom configuration template names. The `.j2` suffix is automatically appended to the names generated from the **‌configlets** dictionary.
```

Finally, you might want to create a variant of a configuration template for a specific provider, and a more generic one for all other providers. That cannot be easily expressed as a dictionary structure, so the **files** plugin treats **base** key as a special case, meaning *do not append anything to the file name*. The following example will thus create **ifup/eos.j2**  and **ifup/eos-clab.j2** files:

```
configlets:
  mgmt:
    eos:
      clab: |
        interface Management0
          description Management interface
      base: |
        interface Management1
          description Management interface
```

## Inline Node/Group Configuration Templates

The **files** plugin allows you to specify the contents of custom configuration templates directly in the node- or group **config** attribute.

If you enabled the **files** plugin, and the content of the **config** attribute is a dictionary, the **files** plugin copies the dictionary into the **configlets** dictionary and replaces it with a list of custom configuration templates (the dictionary keys).

If you don't care about the configuration template names, use the **config.inline** template. **files** plugin will auto-generate a template name and use it to apply extra configuration to the node (or group of nodes) where the **config.inline** template is defined.

For example, the following lab topology creates a template `_n_x1.j2` that is then used to add a route map and extra BGP configuration to X1:

```
plugin: [ files ]
module: [ bgp ]

nodes:
  dut:
    bgp.as: 65000

  x1:
    id: 10
    bgp.as: 65010
    bgp.originate: 172.0.42.0/24
    config.inline: |
      route-map setcomm permit 10
      set community 65000:1 additive
      set extcommunity bandwidth 100
      set large-community 65000:0:1 additive
      exit
      !
      router bgp {{ bgp.as }}
      !
      address-family ipv4 unicast
      {% for n in bgp.neighbors %}
        neighbor {{ n.ipv4 }} route-map setcomm out
      {% endfor %}

  x2:
    id: 11
    bgp.as: 65011
```

```{tip}
Always use the YAML *literal ‌block scalar header* (`|`) for the custom configuration content; otherwise, the whole content will be folded into a single line.
```

## Inline Configuration Changes in Validation Tests

Once the **files** plugin is activated, the validation tests can use the **config.inline** attribute to specify the changes that should be made to the device configuration directly in the validation test, for example:

```
validate:
...
  bgp_lbd:
    description: Shut down the loopback interface
    config:
      inline:
        frr: |
          #!/bin/bash
          ip link set lo down
    pass: BGP prefix is no longer announced
    nodes: [ xf ]
```

```{tip}
Always use the YAML *literal ‌block scalar header* (`|`) for the configuration content; otherwise, the whole content will be folded into a single line.
```


