# Using Containerlab with *netlab*

[Containerlab](https://containerlab.srlinux.dev/) is a Linux-based container orchestration system focused on creating virtual network topologies. To use it:

* Follow the [containerlab installation guide](https://containerlab.srlinux.dev/install/) or use **[netlab install containerlab](../netlab/install.md)** on Ubuntu.
* Install network device container images
* Create [lab topology file](../topology-overview.md). Use `provider: clab` in lab topology to select the *containerlab* virtualization provider.
* Start the lab with **[netlab up](../netlab/up.md)**

## Container Images

Lab topology file created by **[netlab up](../netlab/up.md)** or **[netlab create](../netlab/create.md)** command uses these container images (use **netlab show images** to display the actual system settings):

| Virtual network device | Container image              |
|------------------------|------------------------------|
| Arista cEOS            | ceos:4.26.4M                 |
| Cumulus VX             | networkop/cx:4.4.0           |
| Cumulus VX with NVUE   | networkop/cx:5.0.1           |
| FRR                    | frrouting/frr:v8.3.1         |
| Nokia SR Linux         | ghcr.io/nokia/srlinux:latest |
| Nokia SR OS            | vrnetlab/vr-sros:latest      |

* Cumulus VX, FRR, and Nokia SR Linux images are automatically downloaded from Docker Hub.
* Arista cEOS image has to be [downloaded and installed manually](ceos.md).
* Nokia SR OS container image (requires a license), see also [vrnetlab instructions](https://containerlab.srlinux.dev/manual/vrnetlab/).

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

```{eval-rst}
.. toctree::
   :caption: Installing Container Images
   :maxdepth: 1
   :hidden:

   ceos.md
..
```

## Container runtime support

Containerlab supports [multiple container runtimes](https://containerlab.dev/cmd/deploy/#runtime) besides the default **docker**. The runtime to use can be configured globally or per node, for example:

```
provider: clab
defaults.providers.clab.runtime: podman
nodes:
  s1:
    clab.runtime: ignite
```

## Using File Binds

You can use **clab.binds** to map container paths to host file system paths. Host file paths (dictionary keys) in **clab.binds** might contain dots which would trigger the expansion of keys-with-dots into hierarchical dictionary. To prevent that, all host file paths should have at least one '/' character, for example:

```
nodes:
- name: gnmic
  device: linux
  image: ghcr.io/openconfig/gnmic:latest
  clab:
    binds:
      './gnmic.yaml': '/app/gnmic.yaml:ro'
      '/var/run/docker.sock': '/var/run/docker.sock'
```

### Generating and binding custom config files

In addition to binding pre-existing files, Netlab can also generate custom config files on the fly based on templates.
For example, this is used internally to create the list of daemons for the **frr** container image:

```
frr:
 clab:
  image: frrouting/frr:v8.3.1
  mtu: 1500
  node:
    kind: linux
    config_templates:
      daemons: /etc/frr/daemons
```

```daemons``` references ```templates/provider/clab/frr/daemons.j2``` (```.j2``` is implied); the result gets mapped to /etc/frr/daemons

## Using Other Containerlab Node Parameters

Default *netlab* settings support these additional *containerlab* parameters:

* **clab.type** to set node type (used by Nokia SR OS and Nokia SR Linux)
* **clab.env** to set container environment (used by Arista EOS to set Ethernet interface names)
* **clab.ports** to map container ports to host ports
* **clab.cmd** to execute a command in a container.

String values (for example command to execute specified in **clab.cmd**) are put into single quotes when written into `clab.yml` containerlab configuration file -- make sure you're not using single quotes in your command line.

To add other *containerlab* attributes to the `clab.yml` configuration file, modify **defaults.providers.clab.node_config_attributes** settings, for example:

```
provider: clab
defaults.providers.clab.node_config_attributes: [ ports, env, user ]
```

(clab-linux)=
## Deploying Linux Containers

The initial configuration process (**[netlab initial](../netlab/initial.md)**) no longer relies on commands executed within Linux containers:

* The `/etc/hosts` file is generated during the **[netlab create](../netlab/create.md)** process
* Interface IP addresses and static routes to default gateway are configured with **ip** commands executed on the Linux host but within the container network namespace.

You can therefore use any container image as a Linux node.
