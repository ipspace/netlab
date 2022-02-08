# Using Containerlab with *netsim-tools*

[Containerlab](https://containerlab.srlinux.dev/) is a Linux-based container orchestration system focused on creating virtual network topologies. To use it:

* Follow the [containerlab installation guide](https://containerlab.srlinux.dev/install/) or use **[netlab install containerlab](../netlab/install.md)** on Ubuntu.
* Install network device container images
* Create [lab topology file](../topology-overview.md). Use `provider: clab` in lab topology to select the *containerlab* virtualization provider.
* Start the lab with **[netlab up](../netlab/up.md)**

## Container Images

Lab topology file created by **[netlab up](../netlab/up.md)** or **[netlab create](../netlab/create.md)** command uses these container images:

| Virtual network device | Container image              |
|------------------------|------------------------------|
| Arista cEOS            | ceos:4.25.1F                 |
| Cumulus VX             | networkop/cx:4.3.0           |
| FRR                    | frrouting/frr:v7.5.0         |
| Nokia SR Linux         | ghcr.io/nokia/srlinux:latest |
| Nokia SR OS            | vrnetlab/vr-sros:latest      |

Cumulus VX, FRR, and Nokia SR Linux images are downloaded from Docker Hub.

To install the Arista cEOS container image:

* Download the image from Arista web site
* Import the image with **docker image import _file_ _imagename_**

To install the Nokia SR OS container image (requires a license), see [vrnetlab instructions](https://containerlab.srlinux.dev/manual/vrnetlab/).

You can also use [vrnetlab](https://github.com/vrnetlab/vrnetlab) to build VM-in-container images for Cisco CSR 1000v, Nexus 9300v and IOS XR, OpenWRT, Mikrotik RouterOS, Arista vEOS, Juniper vMX and vQFX, and a few other devices.

## LAN bridges

For multi-access network topologies, **[netlab up](../netlab/up.md)** command automatically creates additional standard Linux bridges. 

You might want to use Open vSwitch bridges instead of standard Linux bridges (OVS interferes less with layer-2 protocols). After installing OVS, set **defaults.providers.clab.bridge_type** to **ovs-bridge**, for example:

```
defaults.device: cumulus

provider: clab
defaults.providers.clab.bridge_type: ovs-bridge

module: [ ospf ]
nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3 ]
```
