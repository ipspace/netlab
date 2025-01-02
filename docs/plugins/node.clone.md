(plugin-node-clone)=
# Dealing with large amounts of identical devices

The *node.clone* plugin avoids tedious repetitive work by allowing users to mark any node for cloning. Any node with a **clone** attribute gets cloned N times, duplicating links and any group memberships.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using the Plugin

* Add `plugin: [ node.clone ]` to the lab topology.
* Include the **clone** attribute in any nodes that need to be replicated multiple times.

The plugin is invoked early in the _netlab_ topology transformation process and updates groups and adds nodes and links to the lab topology.

It is possible to override properties of cloned nodes by including a node with the clone name in the topology. See the example below

### Supported attributes

The naming of cloned nodes can be controlled through global **clone.node_name_pattern**, default "{name[:13]}-{id:02d}".
When customizing, it is recommended to ensure this generates valid DNS hostnames (of max length 16)

The plugin adds the following node attributes:
* **clone.count** is a required int (>0) that defines the number of clones to create
* **clone.start** is the index to start at, default 1
* **clone.step**  is an optional step increase between clones, default 1

### Caveats

The plugin does not support:
* link groups
* cloning of components (nodes composed of multiple nodes)

When custom **ifindex** or **lag.ifindex** values are specified, the plugin automatically increments the value for each clone. This may generate overlapping/conflicting values, which will typically show up as duplicate interface names. It is the user's responsibility to ensure that custom values don't overlap.

Avoid the use of static IPv4/v6 attributes for clones, they are not checked nor automatically updated, and will likely lead to duplicate IP addresses.

## Examples

(host-cluster)=
### Connect Multiple Hosts to a ToR

The following lab topology has a cluster of 10 hosts all connected to a Top-of-Rack switch in the same way.
The clones will be called H-01, H-02, ...

```yaml
plugin: [ node.clone ]

vlans:
 v1:

nodes:
  ToR:
    device: frr
    module: [ vlan ]
  H:
    device: linux
    clone.count: 10
    provider: external  # Mark as 'external' such that no containers get created for these nodes

  H-01:
    provider: clab      # Instantiate only the first node as a container, leave the rest virtual
    
links:
- ToR:
    ifindex: 4          # Start from port 4
    vlan.access: v1
  H:
```
