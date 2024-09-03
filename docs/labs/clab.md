# Using Containerlab with *netlab*

[Containerlab](https://containerlab.srlinux.dev/) is a Linux-based container orchestration system that creates virtual network topologies using containers as network devices. To use it:

* Use **[netlab install containerlab](../netlab/install.md)** on Ubuntu, or follow the [containerlab installation guide](https://containerlab.srlinux.dev/install/) on other Linux distributions.
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

Recent _netlab_ releases were tested with _containerlab_ version 0.55.0. That's also the version the **netlab install containerlab** command installs.

If needed, use ```sudo containerlab version upgrade``` to upgrade to the latest _containerlab_ version.

(clab-images)=
## Container Images

Lab topology file created by **[netlab up](../netlab/up.md)** or **[netlab create](../netlab/create.md)** command uses these container images (use **netlab show images** to display the actual system settings):

| Virtual network device | Container image              |
|------------------------|------------------------------|
| Arista cEOS            | ceos: 4.31.2F                 |
| BIRD                   | netlab/bird:latest           |
| Cisco Catalyst 8000v   | vrnetlab/vr-c8000v:17.13.01a |
| Cisco CSR 1000v        | vrnetlab/vr-csr:17.03.04     |
| Cisco IOS XRd          | ios-xr/xrd-control-plane:7.11.1 |
| Cisco Nexus OS         | vrnetlab/vr-n9kv:9.3.8       |
| Cumulus VX             | networkop/cx:4.4.0           |
| Cumulus VX with NVUE   | networkop/cx:5.0.1           |
| Dell OS10              | vrnetlab/vr-ftosv            |
| dnsmasq                | netlab/dnsmasq:latest        |
| FRR                    | frrouting/frr:v8.4.0         |
| Juniper vMX            | vrnetlab/vr-vmx:18.2R1.9     |
| Juniper vSRX           | vrnetlab/vr-vsrx:23.1R1.8    |
| vJunos-switch          | vrnetlab/vr-vjunosswitch:23.2R1.14 |
| Linux[❗](clab-linux)  | python:3.9-alpine            |
| Mikrotik RouterOS 7    | vrnetlab/vr-routeros:7.6     |
| Nokia SR Linux         | ghcr.io/nokia/srlinux:latest |
| Nokia SR OS            | vrnetlab/vr-sros:latest      |
| VyOS                   | ghcr.io/sysoleg/vyos-container |

* Cumulus VX, FRR, Linux, and Nokia SR Linux images are automatically downloaded from Docker Hub.
* Build the BIRD and dnsmasq images with the **netlab clab build** command.
* Arista cEOS image has to be [downloaded and installed manually](ceos.md).
* Nokia SR OS container image (requires a license); see also [vrnetlab instructions](https://containerlab.srlinux.dev/manual/vrnetlab/).
* Follow Cisco's documentation to install the IOS XRd container, making sure the container image name matches the one _netlab_ uses (alternatively, [change the default image name](default-device-image) for the IOS XRd container).

You can also use [vrnetlab](https://github.com/vrnetlab/vrnetlab) to build VM-in-container images for Cisco CSR 1000v, Nexus 9300v, and IOS XR, OpenWRT, Mikrotik RouterOS, Arista vEOS, Juniper vMX and vQFX, and a few other devices.

```{warning}
* You might have to change the default loopback address pool when using _vrnetlab_ images. See [](clab-vrnetlab) for details.
* The _vrnetlab_ process generates container tags based on the underlying VM image name. You will probably have to [change the container image name](default-device-type) with the **‌defaults.devices._device_.clab.image** lab topology parameter ([more details](tutorial-release)).
```

## Containerlab Networking

### LAN Bridges

The **[netlab up](../netlab/up.md)** command automatically creates additional standard Linux bridges for multi-access network topologies.

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

Lab links are modeled as point-to-point *veth* links or as links to internal Linux bridges. If you want a lab link connected to the outside world, set **clab.uplink** to the name of the Ethernet interface on your server[^IFNAME]. The minimum *containerlab* release supporting this feature is release 0.43.0.

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
In multi-provider topologies, set the **uplink** parameter only for the primary provider (specified in the topology-level **provider** attribute); netlab copies the **uplink** parameter to all secondary providers during the lab topology transformation process.
```

### Containerlab Management Network

*containerlab* creates a dedicated Docker network to connect the container management interfaces to the host TCP/IP stack. You can change the parameters of the management network in the **addressing.mgmt** pool:

* **ipv4**: The IPv4 prefix used for the management network (default: `192.168.121.0/24`)
* **ipv6**: Optional IPv6 management network prefix. It's not set by default.
* **start**: The offset of the first management IP address in the management network (default: `100`). For example, with **start** set to 50, the device with **node.id** set to 1 will get the 51st IP address in the management IP prefix.
* **\_network**: The Docker network name (default: `netlab_mgmt`)
* **\_bridge**: The name of the underlying Linux bridge (default: unspecified, created by Docker)

### Container Management IP Addresses

*netlab* assigns an IPv4 (and optionally IPv6) address to the management interface of each container regardless of whether the container supports SSH access. That IPv4/IPv6 address is used by *containerlab* to configure the first container interface.

You can change a device management interface's IPv4/IPv6 address with the **mgmt.ipv4**/**mgmt.ipv6** node parameter, but be aware that nobody checks whether your change will result in overlapping IP addresses.

It's much better to use the **addressing.mgmt** pool **ipv4**/**ipv6**/**start** parameters to adjust the address range used for management IP addresses and rely on *netlab* to assign management IP addresses to containers based on [device node ID](node-augment).

(clab-port-forwarding)=
### Port Forwarding

*netlab* supports container port forwarding -- mapping of TCP ports on the container management IP address to ports on the host. You can use port forwarding to access the lab devices via the host's external IP address without exposing the management network to the outside world.

```{warning}
Some containers do not run an SSH server and cannot be accessed via SSH, even if you set up port forwarding for the SSH port.
```

Port forwarding is turned off by default and can be enabled by configuring the **defaults.providers.clab.forwarded** dictionary. Dictionary keys are TCP port names (ssh, http, https, netconf), and dictionary values are the starting values of host ports. *netlab* assigns a unique host port to every forwarded container port based on the start value and container node ID.

For example, when given the following topology...

```
defaults.providers.clab.forwarded:
  ssh: 2000

defaults.device: eos
nodes:
  r1:
  r2:
    id: 42
```

... *netlab* maps:
    
* SSH port on management interface of R1 to host port 2001 (R1 gets default node ID 1)
* SSH port on management interface of R2 to host port 2042 (R2 has static ID 42)

(clab-vrnetlab)=
## Using vrnetlab Containers

[_vrnetlab_](https://containerlab.dev/manual/vrnetlab/) is an open-source project that packages network device virtual machines into containers. The resulting containers have a launch process that starts **qemu** (KVM) to spin up a virtual machine. Running *vrnetlab* containers on a VM, therefore, requires nested virtualization.

```{warning}
* _vrnetlab_ has to add another layer of abstraction and [spaghetti networking](vrnetlab-internal-net). If you can choose between a _vrnetlab_ container and a Vagrant box supported by _netlab_, use the Vagrant box.
* Do not use the original _vrnetlab_ project to create device containers. _netlab_ has been tested with the [vrnetlab fork](https://github.com/hellt/vrnetlab) supported by _containerlab_ (see [containerlab documentation](https://containerlab.dev/manual/vrnetlab/) for more details).
* Finally, _vrnetlab_ is an independent open-source project. If it fails to produce a working container image ([example](https://github.com/hellt/vrnetlab/issues/231)), please contact them.
```

### Image Names

The build process generates container tags based on the underlying VM image name. You will probably have to [change the default _netlab_ container image name](default-device-type) with the **‌defaults.devices._device_.clab.image** lab topology parameter.

(vrnetlab-internal-net)=
### Internal Container Networking

The packaged container's architecture requires an internal network. The [_vrnetlab_ fork](https://github.com/hellt/vrnetlab) supported by _containerlab_ uses the IPv4 prefix 10.0.0.0/24 on that network, which clashes with the _netlab_ loopback address pool. Fortunately, that fork also adds management VRF (and default route within the management VRF) to most device configurations, making the overlap between _vrnetlab_ internal subnet and _netlab_ loopback pool irrelevant.

However, if you're still experiencing connectivity problems or initial configuration failures with _vrnetlab_-based containers after rebuilding them with the [latest vrnetlab version](https://github.com/hellt/vrnetlab), add the following parameters to the lab configuration file to change the _netlab_ loopback addressing pool:

```
addressing:
  loopback:
    ipv4: 10.255.0.0/24
  router_id:
    ipv4: 10.255.0.0/24
```

Alternatively, add the same settings to the [user defaults file](defaults-user-file).

### Waiting for the VM

During the **netlab up** process, *containerlab* starts the containers and reports success. The virtual machines in those containers might need minutes to start, which means that _netlab_ cannot continue with the initial configuration process.

_vrnetlab_-based supported platforms go through an extra "_is the device ready_" check during the initial configuration process: _netlab_ tries to establish an SSH session with the device and execute a command. The SSH session is retried up to 20 times, and as each retry usually takes 30 seconds (due to TCP timeouts), **netlab initial** waits up to 10 minutes for a VM to become ready.

If your virtual machines take even longer to boot, increase the number of retries. You can set the **netlab_check_retries** node variable to increase the number of retries for an individual node or set the **defaults.devices._device_.clab.group_vars.netlab_check_retries** variable to increase the number of retries for a specific device (see also [](defaults) and [](defaults-user-file))

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
You don't have to worry about dots in filenames: _netlab_ knows that the keys of the **‌clab.binds** and **‌clab.config_templates** dictionaries are filenames. They are not expanded into hierarchical dictionaries.
```

(clab-config-template)=
### Generating and Binding Custom Configuration Files

In addition to binding pre-existing files, _netlab_ can generate custom config files on the fly based on Jinja2 templates. For example, this is used internally to create the list of daemons for the **frr** container image:

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

In the above example, the `daemons.j2` Jinja2 template from the configuration file templates search path[^CFSP] is rendered into the `daemons` file within the `clab_files/node-name` subdirectory of the current directory. That file is then mapped into the `/etc/frr/daemons` file within the container.

[^CFSP]: See [](dev-config-deploy-paths) for more details.

_netlab_ tries to locate the Jinja2 templates in the device-specific **paths.templates.dir** directories[^CFTD]; the template file name is the dictionary key (for example, `daemons`) with the `.j2` suffix.

[^CFTD]: See [](change-search-paths) for more details.

For example, with the default path settings, the user-specified `daemons.j2` template could be in the `templates/frr` subdirectory of the lab topology directory, the current directory, `~/.netlab` directory or `/etc/netlab` directory.

You can use the ```clab.config_templates``` node attribute to add your own container configuration files[^UG], for example:

[^UG]: As the global provider parameters aren't copied into node parameters, use groups to specify the same configuration templates for multiple devices.

```
provider: clab

nodes:
  t1:
    device: linux
    clab:
      config_templates:
        some_daemon: /etc/some_daemon.cf
```

Faced with the above lab topology, _netlab_ creates ```clab_files/t1/some_daemon``` from ```some_daemon.j2``` (found in the configuration template search path) and maps it to ```/etc/some_daemon.cf``` within the container file system.

### Jinja2 Filters Available in Custom Configuration Files

The custom configuration files are generated within _netlab_ and can use standard Jinja2 filters. If you have Ansible installed as a Python package[^HB], _netlab_ tries to import the **ipaddr** family of filters, making filters like **ipv4**, **ipv6**, or **ipaddr** available in custom configuration file templates.

```{warning}
Ansible developers love to restructure stuff and move it into different directories. This functionality works with two implementations of **ipaddr** filters (tested on Ansible 2.10 and Ansible 7.4/ Ansible Core 2.14) but might break in the future -- we're effectively playing whack-a-mole with Ansible developers.
```

[^HB]: Installing Ansible with Homebrew or into a separate virtual environment won't work -- _netlab_ has to be able to import Ansible modules

(clab-other-parameters)=
### Using Other Containerlab Node Parameters

You can also change these *containerlab* parameters:

* **clab.kind** -- [containerlab device kind](https://containerlab.dev/manual/kinds/). Set in the system defaults for all supported devices; use it only to specify the device type for [unknown devices](platform-unknown).
* **clab.type** to set node type (used by Nokia SR OS and Nokia SR Linux).
* **clab.env** to set container environment (used to [set interface names for Arista cEOS](https://containerlab.dev/manual/kinds/ceos/#additional-interface-naming-considerations))
* **clab.ports** to map container ports to host ports
* **clab.cmd** to execute a command in a container.
* **clab.startup-delay** to make certain node(s) to boot/start later than others (amount in seconds)

```{warning}
String values (for example, the command to execute specified in **clab.cmd**) are put into single quotes when written into the `clab.yml` containerlab configuration file. Ensure you're not using single quotes in your command line.
```

The complete list of supported Containerlab attributes is in the [system defaults](https://github.com/ipspace/netlab/blob/dev/netsim/providers/clab.yml#L22) and can be printed with the `netlab show defaults providers.clab.attributes` command.

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
