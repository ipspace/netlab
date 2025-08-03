(plugin-files)=
# Embed Files and Configuration Templates in Lab Topology

The **files** plugin allows you to include small files and custom configuration templates directly in the lab topology, enabling the deployment of a complete solution as a single lab topology file.

The plugin defines two new topology attributes:

* **files** -- a dictionary or list of extra files to create in the lab directory
* **configlets** -- a dictionary of custom configuration templates

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
  ifup: ip link set eth1 up
  ifdown: ip link set eth1 down
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

Finally, you might want to create a variant of a configuration template for a specific provider, and a more generic one for all other providers. That cannot be easily expressed as a dictionary structure, so the **files** plugin treats **content** key as a special case, meaning *do not append anything to the file name*. The following example will thus create **ifup/eos.j2**  and **ifup/eos-clab.j2** files:

```
configlets:
  mgmt:
    eos:
      clab: |
        interface Management0
          description Management interface
      content: |
        interface Management1
          description Management interface
```
