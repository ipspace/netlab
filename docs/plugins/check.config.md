(plugin-check-config)=
# Check Custom Configuration Templates

The **check.config** plugin verifies that the multi-platform custom configuration templates exist for the devices used in the current lab topology. Use it in lab topologies that provide custom configuration templates for a subset of *netlab*-supported devices to prevent errors in the **[netlab initial](netlab-initial-custom)** Ansible playbook.

The plugin iterates over the node **config** lists and tries to find configuration templates for every item in the config list. It checks the following files using the **paths.custom** search path[^DSP]:

| File name      | Meaning |
|----------------|---------|
| config/node.device.j2 | Node-and-device specific configuration |
| config/node.j2 | Node-specific configuration applied to all device types |
| config/device.j2 | Device-specific configuration applied to all nodes |

[^DSP]: Use **netlab show defaults paths.custom** or **netlab inspect defaults.paths.custom** to display the custom configuration template search path.

The items in the file names are derived from the following data:

| Item   | Source  |
|--------|---------|
| config | Custom configuration template name from the **config** list |
| node   | Node name (**nodes** dictionary key) |
| device | Node **device** attribute |

The plugin removes custom configuration templates without matching template files from the node **config** list and generates summary warnings specifying which templates are missing for individual device types and which nodes are affected.

```{tip}
**‌netlab initial** and **‌netlab config** commands accept a wider range of valid template filenames, including templates in the topology directory, provider-specific templates, and multi-platform templates (for example, **‌ios.j2** template can be used for **‌iosv**, **‌iosvl2**, **‌csr**, and **‌cat8000v**). You cannot use these options with the **‌check.config** plugin.
```
