(tools-graphite)=
# Graphite

Graphite is a network visualizer for emulated topologies. Use this tool as _netlab_ GUI.

* Add the following lines to the lab topology file to enable Graphite:

```
tools:
  graphite:
```

* The URL used to connect to Graphite web server is printed during **netlab up** process. You can also print it with **netlab connect graphite** command.
* Graphite tool has no configurable parameters
* Graphite includes web-based SSH access to lab devices. The lab devices have to be reachable from within the Docker container, and must have unique IP addresses. 

## Modifying Graph Attributes

The following attributes are recognized by the *graphite* output module:

* **graphite.icon**: Node Icon used in the graph -- specified for individual nodes, as part of group data, or as device default (**defaults.devices._device_.graphite.icon**). You can use these icon types (from [Cisco DevNet NeXT UI API doc](https://developer.cisco.com/site/neXt/document/api-reference-manual/files/src_js_graphic_svg_Icons.js/#l11)):

  * switch
  * router
  * wlc
  * unknown
  * server
  * phone
  * nexus5000
  * ipphone
  * host
  * camera
  * accesspoint
  * groups
  * cloud
  * firewall
  * hostgroup
  * wirelesshost

* **graphite.level**: Node Level within the graph. Can be specified for individual nodes or as part of **node_data** in groups; default value is `1`.

## Topology Example

```
module: [ bgp, ospf ]
bgp.as: 65000

nodes:
  a:
  b:
  c:
  d:
  rr:
    bgp.rr: True
    id: 1
    graphite.icon: server
  y:
    bgp.as: 65100
    module: [ bgp ]
    graphite.level: 2
  linux1:
    module: []
    device: linux
    graphite.icon: host
    graphite.level: 3
  linux2:
    module: []
    device: linux
    graphite.level: 3
  linux3:
    module: []
    device: linux
    graphite.level: 3

links:
- a-b
- a-c
- b-d
- c-d
- b-rr
- d-rr
- c-y
- d-y
- y-linux1
- y:
  linux2:
  linux3:
- y:
```
