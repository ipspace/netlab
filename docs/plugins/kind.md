(plugin-kind)=
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

## Other Networking Parameters

* IPv4/IPv6 forwarding is enabled on the KinD containers. To disable it, set the **netlab_ip_forwarding** parameter of the cluster node to *False* ([more details](linux-forwarding)), for example:

```
provider: clab
plugin: [ kind ]

nodes:
  kc:
    device: kind
    kind.workers: 2
    netlab_ip_forwarding: False
```

* KinD containers do not have loopback interfaces. To add the loopback interface to KinD containers, set the **loopback** parameter of the cluster node to *True*.

## Additional Cluster Node Parameters

You can influence the parameters of the control plane or worker nodes using the attributes of the cluster node. The following parameters are copied from the cluster node (device *kind*) to KinD containers:

* The **box**, **role**, and **loopback** parameters
* The **routing** dictionary (allowing you to specify custom static routes)
* All parameters starting with **netlab\_** (allowing you to disable IP forwarding).

## Setting Parameters on Individual KinD Containers

You can also change the parameters of individual KinD containers:

* Add them to the lab topology (use the node names the plugin will use)
* Set the node **device** to *kind-node* if you haven't specified the default device in the lab topology.
* Set the parameters you want to change, for example, **clab.exec** to execute commands on individual containers once they're started.

Example:

```
provider: clab
plugin: [ kind ]

nodes:
  kc:
    device: kind
    kind.workers: 2
  kc-control-plane:
    clab.exec:
    - echo "hello, world"
    device: kind-node
```

```{warning}
You cannot use **‌clab.binds** or **‌clab.config_templates** parameters; containerlab does not use these parameters on members of KinD clusters.
```
