# Graphite Topology Output Module

Why use [Graphite](https://github.com/netreplica/graphite) only with ContainerLab? :-)

*graphite* output module creates a JSON file that can be used to display the *netsim-tools* lab topology within Graphite.

By default, the output is created as *graphite-default.json* file, which can be used directly from the Graphite container. Additionally, using the container *graphite:webssh2*, it is possible to launch SSH sessions towards the nodes directly from the browser.

The Graphite container can be launched with:
```
docker run -d \
 -v "$(pwd)/graphite-default.json":/var/www/localhost/htdocs/default/default.json \
 -p 8080:80 \
 --name graphite \
 netreplica/graphite:webssh2
```

And you can access the Graphite WebGUI from: `http://<LOCAL_IP>:8080/graphite/`.

## Modifying Graph Attributes

The following attributes are allowed, at node level, or as **defaults** settings.
* **graphite.icon**: Node Icon on the graph. Possible icon types are (from [Cisco DevNet NeXT UI API doc](https://developer.cisco.com/site/neXt/document/api-reference-manual/files/src_js_graphic_svg_Icons.js/#l11)):
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
* **graphite.level**: Node Level on the graph (can be specified only at node level - defaults to `1`).

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