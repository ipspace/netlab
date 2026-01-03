# Kubernetes Cluster in Container Nodes

The *kind* plugin implements Kubernetes in Docker (KinD) cluster for *containerlab* deployments.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using the Plugin

* Add `plugin: [ kind ]` to lab topology. The plugin adds **kind** device that can be used to deploy a Kubernetes cluster
* Add a node with **device: kind** to the lab topology. The *kind* plugin will automatically create control-plane and worker nodes.
* Set the number of worker nodes in the cluster with the **kind.workers** node parameter. Without this parameter, the plugin deploys a single-node Kubernetes cluster

For example, the following topology deploys a 3-node cluster with no external connectivity (the cluster is connected to the *kind* Docker network created by *containerlab*):

```
provider: clab
plugin: [ kind ]

nodes:
  kc:
    device: kind
    kind.workers: 2

```

The names of the cluster members are derived from the cluster name. In our example, the three containers would be named *kc-control-plane*, *kc-worker* and *kc-worker2*:

```
$ docker ps
CONTAINER ID   IMAGE                          COMMAND                  CREATED          STATUS          PORTS                       NAMES
49f3a87d7742   kindest/node:v1.34.3           "/usr/local/bin/entr…"   11 minutes ago   Up 10 minutes   127.0.0.1:35301->6443/tcp   kc-control-plane
832e14fe9842   kindest/node:v1.34.3           "/usr/local/bin/entr…"   11 minutes ago   Up 10 minutes                               kc-worker2
509551e5ca05   kindest/node:v1.34.3           "/usr/local/bin/entr…"   11 minutes ago   Up 10 minutes                               kc-worker
```

## Lab Connectivity

You can connect the KinD cluster node to any number of *netlab* links. When creating the control-plane and worker nodes, the *kind* plugin automatically connects them to the same links *if the links are stub or LAN links*. For point-to-point links, the *kind* plugin replaces the link between the cluster node and another node with a series of point-to-point links.

For example, _netlab_ creates three links when given this topology:

```
provider: clab
plugin: [ kind ]

nodes:
  kc:
    device: kind
    kind.workers: 2
  sw:
    device: frr

links: [ kc-sw ]
```

| Link Name       | Origin Device | Origin Port | Destination Device | Destination Port |
|-----------------|---------------|-------------|--------------------|------------------|
|                 | kc-control-plane | eth1        | sw                 | eth1             |
|                 | kc-worker     | eth1        | sw                 | eth2             |
|                 | kc-worker2    | eth1        | sw                 | eth3             |

On the other hand, the following topology using a LAN link results in all three cluster nodes connected to the same switch port:

```
provider: clab
plugin: [ kind ]

nodes:
  kc:
    device: kind
    kind.workers: 2
  sw:
    device: frr

links: 
- interfaces: [ kc, sw ]
  type: lan
```

| Origin Device | Origin Port | Link Name (NET) | Description          |
|---------------|-------------|-----------------|----------------------|
| sw            | eth1        | X_1             | sw -> [kc-control-plane,kc-worker,kc-worker2] |
| kc-control-plane | eth1        | X_1             | kc-control-plane -> [sw,kc-worker,kc-worker2] |
| kc-worker     | eth1        | X_1             | kc-worker -> [sw,kc-control-plane,kc-worker2] |
| kc-worker2    | eth1        | X_1             | kc-worker2 -> [sw,kc-control-plane,kc-worker] |

```{warning}
The current version of the plugin does not configure IP addresses or static routes on the cluster nodes.
```
