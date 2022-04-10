# Graphite Topology Output Module

*graphite* output module creates a JSON file that can be used to display the *netsim-tools* lab topology within [Graphite](https://github.com/netreplica/graphite).

By default, the output is created as *graphite-default.json* file, which can be used directly from the Graphite container. When using the *graphite:webssh2* container, you can open SSH sessions with lab devices running in *libvirt* environment directly from the browser, making your lab accessible from an external IP network without routing or port-mapping tricks.

After creating the lab topology with `netlab create -o graphite`, launch the Graphite container with:

```
docker run -d \
 -v "$(pwd)/graphite-default.json":/var/www/localhost/htdocs/default/default.json \
 -p 8080:80 \
 --name graphite \
 netreplica/graphite:webssh2
```

After the Docker container has been launched, you can access the Graphite WebGUI from: `http://<LOCAL_IP>:8080/graphite/`.

## SSH Access to Lab Devices

*graphite:webssh2* container includes web-based SSH access to lab devices. The web devices have to be reachable from within the Docker container, and must have unique IP addresses. 

In this release, SSH access to lab devices works only with *libvirt*-based labs:

* Vagrant uses different TCP ports on *localhost* to access lab devices in VirtualBox labs. Graphite does not support custom SSH ports. 
* Containerlab uses a Docker management network (*clab*) that cannot be accessed by containers connected to the *bridge* network. You could fix Docker network settings, but it's easier to use **sudo containerlab graph -t clab.yml** to run *graphite* within *containerlab*.

## Modifying Graph Attributes

The following attributes are recognized by the *graphite* output module:

* **graphite.icon**: Node Icon used in the graph -- specified for individual nodes, as part of **node_data** in groups, or as device default (**defaults.devices._device_.graphite.icon**). You can use these icon types (from [Cisco DevNet NeXT UI API doc](https://developer.cisco.com/site/neXt/document/api-reference-manual/files/src_js_graphic_svg_Icons.js/#l11)):

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