# Containerlab

[Containerlab](https://containerlab.srlinux.dev/) is a Linux-based container orchestration system focused on creating virtual network topologies. To use it:

* Follow the [containerlab installation guide](https://containerlab.srlinux.dev/install/)
* Install network device container images
* Create [lab topology file](../topology-overview.md). Use `provider: clab` in lab topology to select the *containerlab* virtualization provider.
* Create *containerlab* topology file (`clab.yml`) with **netlab create** command
* Start the lab with **sudo containerlab deploy** command

## Container Images

Lab topology file created by **netlab create** command uses these container images:

| Virtual network device | Container image      |
|------------------------|----------------------|
| Arista cEOS            | ceos:4.25.1F         |
| FRR                    | frrouting/frr:v7.5.0 |

To install the Arista cEOS container image:

* Download the image from Arista web site
* Import the image with **docker image import _file_ _imagename_**
