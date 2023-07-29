# Using Containerlab with *netlab*

[Containerlab](https://containerlab.srlinux.dev/) is a Linux-based container orchestration system focused on creating virtual network topologies. To use it:

* Follow the [containerlab installation guide](https://containerlab.srlinux.dev/install/) or use **[netlab install containerlab](../netlab/install.md)** on Ubuntu.
* Install network device container images
* Create [lab topology file](../topology-overview.md). Use `provider: clab` in lab topology to select the *containerlab* virtualization provider.
* Start the lab with **[netlab up](../netlab/up.md)**

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported Versions

We tested _netlab_ with _containerlab_ version 0.41.2. That's also the version installed by the **netlab install containerlab** command.

Minimum supported _containerlab_ version is 0.37.1 (2023-2-27) -- that version introduced some changes to the location of generated certificate files.

If needed, use ```sudo containerlab version upgrade``` to upgrade to the latest _containerlab_ version.

## Container Images

Lab topology file created by **[netlab up](../netlab/up.md)** or **[netlab create](../netlab/create.md)** command uses these container images (use **netlab show images** to display the actual system settings):

| Virtual network device | Container image              |
|------------------------|------------------------------|
| Arista cEOS            | ceos:4.26.4M                 |
| Cumulus VX             | networkop/cx:4.4.0           |
| Cumulus VX with NVUE   | networkop/cx:5.0.1           |
| Dell OS10              | vrnetlab/vr-ftosv            |
| FRR                    | frrouting/frr:v8.4.0         |
| Juniper vMX            | vrnetlab/vr-vmx:18.2R1.9     |
| Juniper vSRX           | vrnetlab/vr-vsrx:23.1R1.8    |
| Linux[❗](clab-linux)  | python:3.9-alpine            |
| Mikrotik RouterOS 7    | vrnetlab/vr-routeros:7.6     |
| Nokia SR Linux         | ghcr.io/nokia/srlinux:latest |
| Nokia SR OS            | vrnetlab/vr-sros:latest      |
| VyOS                   | ghcr.io/sysoleg/vyos-container |

* Cumulus VX, FRR, Linux, and Nokia SR Linux images are automatically downloaded from Docker Hub.
* Arista cEOS image has to be [downloaded and installed manually](ceos.md).
* Nokia SR OS container image (requires a license), see also [vrnetlab instructions](https://containerlab.srlinux.dev/manual/vrnetlab/).

You can also use [vrnetlab](https://github.com/vrnetlab/vrnetlab) to build VM-in-container images for Cisco CSR 1000v, Nexus 9300v and IOS XR, OpenWRT, Mikrotik RouterOS, Arista vEOS, Juniper vMX and vQFX, and a few other devices.

```{warning}
You might have to change the default loopback address pool when using _vrnetlab_ images. See [](clab-vrnetlab) for details.
```

## Containerlab Networking

### LAN Bridges

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

(clab-network-external)=
### Connecting to the Outside World

Lab links are modeled as point-to-point *veth* links or as links to internal Linux bridges. If you want to have a lab link connected to the outside world, set **clab.uplink** to the name of the Ethernet interface on your server[^IFNAME]. The minimum *containerlab* release supporting this feature is release 0.43.0.

Example: use the following topology to connect your lab to the outside world through `r1` on a Linux server that uses `enp86s0` as the name of the Ethernet interface:

```
defaults.device: cumulus
provider: clab
nodes: [ r1,r2 ]
links:
- r1-r2
- r1:
  clab:
    uplink: enp86s0
```

[^IFNAME]: Use **ip addr** or **ifconfig** find the interface name.

```{note}
In multi-provider topologies set the **uplink** parameter only for the primary provider (the one specified in topology-level **provider** attribute); netlab copies the **uplink** parameter  to all secondary providers during the lab topology transformation process.
```

### Containerlab Management Network

*containerlab* creates a dedicated Docker network to connect the container management interfaces to the host TCP/IP stack. You can change the parameters of the management network in the **addressing.mgmt** pool:

* **ipv4**: The IPv4 prefix used for the management network (default: `192.168.121.0/24`)
* **ipv6**: Optional IPv6 management network prefix. Not set by default.
* **start**: The offset of the first management IP address in the management network (default: `100`). For example, with **start** set to 50, the device with **node.id** set to 1 will get 51st IP address in the management IP prefix.
* **\_network**: The Docker network name (default: `netlab_mgmt`)
* **\_bridge**: The name of the underlying Linux bridge (default: unspecified, created by Docker)

### Container Management IP Addresses

*netlab* assigns an IPv4 (and optionally IPv6) address to the management interface of each container regardless of whether the container supports SSH access or not. That IPv4/IPv6 address is used by *containerlab* to configure the first container interface.

You can change the IPv4/IPv6 address of a device management interface with the **mgmt.ipv4**/**mgmt.ipv6** node parameter, but be aware that nobody checks whether your change will result in overlapping IP addresses.

It's much better to use the **addressing.mgmt** pool **ipv4**/**ipv6**/**start** parameters to adjust the address range used for management IP addresses, and rely on *netlab* to assign management IP addresses to containers based on [device node ID](node-augment).

(clab-vrnetlab)=
### Using vrnetlab Containers

_vrnetlab_ is an open-source project that packages network device virtual machines into containers. The architecture of the packaged container requires an internal network, and it seems that _vrnetlab_ (or the fork used by _containerlab_) uses IPv4 prefix 10.0.0.0/24 on that network which clashes with the _netlab_ loopback address pool.

If you're experiencing connectivity problems or initial configuration failures with _vrnetlab_-based containers, add the following parameters to the lab configuration file to change the _netlab_ loopback addressing pool:

```
addressing:
  loopback:
    ipv4: 10.255.0.0/24
  router_id:
    ipv4: 10.255.0.0/24
```

## Advanced Topics

### Container Runtime Support

Containerlab supports [multiple container runtimes](https://containerlab.dev/cmd/deploy/#runtime) besides the default **docker**. The runtime to use can be configured globally or per node, for example:

```
provider: clab
defaults.providers.clab.runtime: podman
nodes:
  s1:
    clab.runtime: ignite
```

### Using File Binds

You can use **clab.binds** to map container paths to host file system paths, for example:

```
nodes:
- name: gnmic
  device: linux
  image: ghcr.io/openconfig/gnmic:latest
  clab:
    binds:
      gnmic.yaml: '/app/gnmic.yaml:ro'
      '/var/run/docker.sock': '/var/run/docker.sock'
```

```{tip}
You don't have to worry about dots in filenames: _netlab_ knows that the keys of the **‌clab.binds** and **‌clab.config_templates** dictionaries are filenames and does not expand them into hierarchical dictionaries.
```

(clab-config-template)=
### Generating and Binding Custom Configuration Files

In addition to binding pre-existing files, _netlab_ can also generate custom config files on the fly based on Jinja2 templates. For example, this is used internally to create the list of daemons for the **frr** container image:

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

_netlab_ tries to locate the templates in the current directory, in a subdirectory with the name of the device, and within system directory ```templates/provider/clab/<device>```. ```.j2``` suffix is always appended to the template name.

For example, the ```daemons``` template used in the above example could be ```./daemons.j2```, ```./frr/daemons.j2``` or ```<netsim_moddir>/templates/provider/clab/frr/daemons.j2```; the result gets mapped to ```/etc/frr/daemons``` within the container file system.

You can use the ```clab.config_templates``` node attribute to add your own container configuration files[^UG], for example:

[^UG]: As the global provider parameters aren't copied into node parameters, use groups to specify the same set of configuration templates for multiple devices.

```
provider: clab

nodes:
  t1:
    device: linux
    clab:
      config_templates:
        some_daemon: /etc/some_daemon.cf
```

Faced with the above lab topology, _netlab_ creates ```clab_files/t1/some_daemon``` from ```some_daemon.j2``` (the template could be either in current directory or ```linux``` subdirectory) and maps it to ```/etc/some_daemon.cf``` within the container file system.

### Jinja2 Filters Available in Custom Configuration Files

The custom configuration files are generated within _netlab_ and can therefore use standard Jinja2 filters. If you have Ansible installed as a Python package[^HB], _netlab_ tries to import **ipaddr** family of filters, making filters like **ipv4**, **ipv6** or **ipaddr** available in custom configuration file templates.

```{warning}
Ansible developers love to restructure stuff and move it into different directories. This functionality works with two implementations  of **ipaddr** filters (tested on Ansible 2.10 and Ansible 7.4/ Ansible Core 2.14) but might break in the future -- we're effectively playing whack-a-mole with Ansible developers.
```

[^HB]: Installing Ansible with Homebrew or into a separate virtual environment won't work -- _netlab_ has to be able to import Ansible modules

### Using Other Containerlab Node Parameters

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

```{eval-rst}
.. toctree::
   :caption: Installing Container Images
   :maxdepth: 1
   :hidden:

   ceos.md
   linux.md
..
```
