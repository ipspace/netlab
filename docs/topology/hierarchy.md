# Hierarchical Dictionaries in *netlab* YAML files

*netlab* describes network topology with a complex data structures encoded as a combination of hierarchical dictionaries and lists. Such a data structure is easy to encode in YAML but could be hard to read due to the many levels of dictionary hierarchy.

*netlab* uses a simple trick to make the topology (and defaults) files more readable: every dictionary key that contains a dot[^NS] is expanded into a hierarchical dictionary that is merged with the rest of the data structure.

For example, you could use **defaults.device** key instead of a dictionary to set the default lab device instead of a more complex setup shown below:

```
defaults:
  device: eos

nodes: [ r1, r2]
```

The hierarchical dictionaries created from dotted attribute names are merged back with the topology data structure, allowing you to use the same prefix in multiple keys, for example:

```
defaults.device: eos
defaults.devices.eos.libvirt.image: vEOS:4.27.0M
defaults.devices.eos.clab.image: cEOS:4.27.0M
defaults.devices.eos.memory: 8192
```

The above settings are identical to the following structured YAML:

```
defaults:
  device: eos
  devices:
    eos:
      libvirt:
        image: vEOS.4.27.0M
      clab:
        image: cEOS:4.27.0M
      memory: 8192
```

The dotted attributes could appear anywhere in the topology hierarchy. For example, you could use them to set node or link attributes:

```
nodes:
  r1:
    bgp.as: 65000
    ospf.area: 1
    
links:
- r1:
  vlan.access: red
```

The above snippet is equivalent to the following traditional YAML data structure:

```
nodes:
  r1:
    bgp:
      as: 65000
    ospf:
      area: 1

links:
- r1:
  vlan:
    access: red
```

[^NS]: ... but not a slash -- we don't want to do that on filenames