(dev-attribute-validation)=
# Lab Topology Attribute Validation

_netlab_ includes a comprehensive validation framework that checks attributes of all core topology elements and optional configuration modules. Valid attributes, their data types, and other constraints are defined in the `attributes` dictionary within the `topology-defaults.yml` file and individual module definitions.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

```{include} validation-basics.txt
```
```{include} validation-types.txt
```
```{include} validation-shortcut.txt
```
```{include} validation-udt.txt
```
```{include} validation-alt.txt
```
```{include} validation-ip.txt
```
(dev-valid-special-keys)=
## Special Attribute Dictionary Keys

The attribute dictionaries can contain these special keys:

* **_namespace**: a list of additional namespaces recognized within the object. For example, the **vlan** object can contain **link** attributes (see `netlab show attributes vlan --format yaml` for an example)
* **_description**: object description displayed in the **netlab show attributes** printout (see `netlab show attributes _v_entry --format yaml` for an example)
