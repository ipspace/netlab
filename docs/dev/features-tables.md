# Auto-Generated "Supported Features" Tables

The `features` Sphinx directive generates the _supported features_ tables for the [](supported-platforms) document and the module descriptions.

```{warning}
The current implementation does not support provider-specific features.
```

The `features` directive is invoked with the [MyST directive syntax](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html#syntax-directives):

````md
```{features}
```
````

The directive content is a YAML-formatted description of the features that should be included in the table, for example:

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

* **title** (required) -- the column header
* **enabled** (required) -- the Python expression that results in a truthy value if the feature works on the device. The expression can use all device definition data (for example, `libvirt.image`), and the device features (for example, `ospf.areas`)
* **caveats** (optional) -- the Python expression that checks whether the device/feature entry should include a link to caveats. The value of the specified device feature could be **true**, in which case the link pointing to the caveat is `caveats-_device_`, or a documentation anchor ID.

When dealing with the parent/child devices (for example, Cisco IOS or Junos platforms), the `features` directive automatically detects whether a child device supports a different set of features than the parent device, removes child devices that inherit feature settings from their parents, and creates a "this parent device includes these other devices" footnote.

Two other device parameters influence the auto-generated "supported features" tables:

* **docname** is a shorter device name (between device code and full device description). For example, Arista EOS has `eos` device code, "Arista vEOS VM or cEOS container" **description**, and "Arista EOS" **docname**.
* Sometimes, you don't want a device to be displayed like a parent device in the features table. For example, the `sonic` device uses `frr` as its parent, but we'd definitely not want to have "FRR includes SONiC" as a footnote. In these cases, set the **docparent** parameter of the parent device to `False`.
