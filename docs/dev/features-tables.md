# Auto-Generated "Supported Features" Tables

The `features` Sphinx directive generates the _supported features_ tables for the [](supported-platforms) document and the module/plugin descriptions.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Creating and Describing Feature Tables

The `features` directive is invoked with the [MyST directive syntax](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html#syntax-directives):

````md
```{features}
```
````

The `{features}` directive content is a YAML-formatted description of the features that should be included in the table, for example:

````md
```{features}
- title: BFD<br>protocol
  enabled: bfd
  caveats: bfd.caveats
- title: OSPF<br>with BFD
  enabled: ospf and bfd
- title: IS-IS<br>with BFD
  enabled: isis and bfd
- title: BGP<br>with BFD
  enabled: bgp.bfd
  caveats: bgp.bfd.caveats
```
````

Each column definition (feature) can have these parameters:

* **title** (required) -- the column header. Use `<br>` to create multi-line headers.
* **enabled** or **text** (exactly one required) -- see below
* **caveats** (optional) -- the Python expression that checks whether the device/feature entry should include a link to caveats. The value of the specified device feature could be **true**, in which case the link pointing to the caveat is `caveats-_device_`, or a documentation anchor ID.

### Feature Display Modes

The directive supports two mutually exclusive modes for displaying feature data:

* **enabled** -- the Python expression that results in a truthy value if the feature works on the device. The cell is displayed as a green checkmark or a red cross. The expression can use all device definition data (for example, `libvirt.image`) and the device features (for example, `ospf.areas`).
* **text** -- the Python expression whose result is displayed as text in the table cell. Lists are joined with commas, booleans are converted to checkmarks/crosses, and other values are converted to strings. Use this when you need to display non-boolean information (like deployment methods or configuration modes).

For example, to display the list of non-default configuration deployment methods:

````md
```{features}
- title: Alternate<br>deployment method
  text: >-
    [ x for x in initial.config_mode if x != group_vars.get('netlab_config_mode','') ]
```
````

### Caveats

The **caveats** parameter links a cell to an explanation of feature limitations. A truthy caveat value generates a link to an anchor with ID `caveats-_device_` (usually defined in `caveats.md`). A string value is used as the link target. A caveat value of `yes` generates a warning emoji with no link (for caveats explained below the table).

### Built-in Functions

The `enabled` and `text` expressions can use the `len()` built-in function. For example:

````md
```{features}
- title: router
  enabled: >-
    "router" in initial.roles and len(initial.roles) > 1
```
````

### Provider-Specific Features

The directive supports provider-specific features. When a device has provider-specific data or feature definitions (for example, `clab.features` or `libvirt.features`), the directive generates additional rows for that device/provider combination, displayed as "Device (containers)" or "Device (VMs)".

Child device deduplication also works at the provider-specific level: if a child device's provider-specific features match its parent's, the child row is removed.

### Parent/Child Device Handling

When dealing with parent/child devices (for example, Cisco IOS or Junos platforms), the `features` directive automatically:

1. Detects whether a child device supports a different set of features than the parent device
2. Removes child devices that inherit feature settings from their parents
3. Creates a "this parent device includes these other devices" footnote

Two device parameters influence this behavior:

* **docname** is a shorter device name (between device code and full device description). For example, Arista EOS has `eos` device code, "Arista vEOS VM or cEOS container" **description**, and "Arista EOS" **docname**.
* Sometimes, you don't want a device to be displayed like a parent device in the features table. For example, the `sonic` device uses `frr` as its parent, but we'd definitely not want to have "FRR includes SONiC" as a footnote. In these cases, set the **docparent** parameter of the parent device to `False`.

## Developing New Feature Tables

The best way to develop a new feature table is to study existing examples. Here are the common patterns:

### Simple Boolean Features

Check whether a device supports a feature by referencing a dotted attribute path within the `features` device dictionary.

````md
```{features}
- title: BGP<br>timers
  enabled: bgp.timers
- title: BFD
  enabled: bgp.bfd
```
````

### Complex Boolean Expressions

Use Python operators for more sophisticated checks:

````md
```{features}
- title: IPv4 DNS<br>client
  enabled: |
    services.dns is True or 'ipv4' in services.dns
- title: IPv6 DNS<br>client
  enabled: |
    services.dns is True or 'ipv6' in services.dns
```
````

### Checking List Membership

Use `in` to check whether a feature is in a list of supported values:

````md
```{features}
- title: "on"
  enabled: 'on' in bgp.remove_private_as.valid
- title: all
  enabled: 'all' in bgp.remove_private_as.valid
```
````

### Using .get() with Defaults

Use `.get()` when a feature attribute might not exist, and you need a default value:

````md
```{features}
- title: Transport<br>VRF
  enabled: |
    services.dns and services.get('dns.transport_vrf',True) != False
```
````

### Combining "enabled" with Caveats

Link cells to caveats when a feature has known limitations:

````md
```{features}
- title: Route<br>import
  enabled: bgp['import']
  caveats: bgp.caveats['import']
- title: Graceful<br>Restart
  enabled: bgp.gr
  caveats: bgp.gr.caveats
```
````

### Displaying Text Values

Use **text** instead of **enabled** when you need to show non-boolean data:

````md
```{features}
- title: Alternate<br>deployment method
  text: >-
    [ x for x in initial.config_mode if x != group_vars.get('netlab_config_mode','') ]
```
````

## Testing Feature Tables

To test a feature table, build the documentation and inspect the rendered output. The following text assumes you're working in the `docs` directory:

1. **Add the new *features* table** next to the original table. The new table should match the original one unless we were sloppy and forgot to update feature tables (in which case device settings/code are the final arbiter).
2. **Build the documentation** with `make html` ([more details](dev-testing-docs)). When modifying device data, `touch` the `.md` file to trigger the build process
2. **Open the relevant page** in `_build/html/` in your browser and verify the table looks correct.
3. **Iterate**: edit the feature table YAML, rebuild, and compare the output until the table matches the expected result.
4. **Remove** the original table once you're done.

### Debugging

* Set the `NETLAB_DEBUG_FEATURES` environment variable to get debug output during the build. The variable accepts comma-separated flags:

   ```bash
   NETLAB_DEBUG_FEATURES=df_data,df_row make html
   ```

   * `df_data` -- dumps per-device feature data and provider-specific checks
   * `df_row` -- dumps the computed feature row for each device

* A useful technique when developing a new feature table is to include a **reference table** (a manually curated table showing the expected output) below the auto-generated one. Compare the two, adjust the YAML expressions or device settings, rebuild, and repeat until the output matches. Once satisfied, remove the reference table.
