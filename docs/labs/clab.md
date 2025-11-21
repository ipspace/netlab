(lab-clab)=
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

The latest _netlab_ release was tested with _containerlab_ version 0.59.0. That's also the version the **netlab install containerlab** command installs.

If needed, use ```sudo containerlab version upgrade``` to upgrade to the latest _containerlab_ version.

(clab-images)=
## Container Images

Lab topology file created by **[netlab up](../netlab/up.md)** or **[netlab create](../netlab/create.md)** command uses these container images (use **netlab show images** to display the actual system settings):

| Virtual network device | Container image              |
|------------------------|------------------------------|
| Arista cEOS            | ceos:4.31.2F                 |
| Aruba CX               | vrnetlab/aruba_arubaos-cx:20240731173624 |
| BIRD                   | netlab/bird:latest           |
| Cisco 8000v            | cisco/cisco-8201-32fh:24.4.1 |
| Cisco Catalyst 8000v   | vrnetlab/vr-c8000v:17.13.01a |
| Cisco CSR 1000v        | vrnetlab/vr-csr:17.03.04     |
| Cisco IOL [❗](caveats-iol)    | vrnetlab/cisco_iol:17.12.01 |
| Cisco IOL L2 [❗](caveats-iol) | vrnetlab/cisco_iol:L2-17.12.01 |
| Cisco IOSv             | vrnetlab/cisco_vios:15.9.3   |
| Cisco IOS XRd          | ios-xr/xrd-control-plane:7.11.1 |
| Cisco Nexus OS         | vrnetlab/vr-n9kv:9.3.8       |
| Cumulus VX             | networkop/cx:4.4.0           |
| Cumulus VX with NVUE   | networkop/cx:5.0.1           |
| Dell OS10              | vrnetlab/vr-ftosv            |
| dnsmasq                | netlab/dnsmasq:latest        |
| Fortinet FortiOS       | vrnetlab/vr-fortios:7.4.8    |
| FRR                    | quay.io/frrouting/frr:10.1.2 |
| Juniper vMX            | vrnetlab/vr-vmx:18.2R1.9     |
| Juniper vPTX           | vrnetlab/juniper_vjunosevolved:23.4R2-S2.1 |
| Juniper vSRX           | vrnetlab/vr-vsrx:23.1R1.8    |
| vJunos-router          | vrnetlab/juniper_vjunos-router:23.4R2-S2.1 |
| vJunos-switch          | vrnetlab/juniper_vjunos-switch:23.4R2-S2.1 |
| Linux[❗](clab-linux)  | python:3.9-alpine            |
| Mikrotik RouterOS 7    | vrnetlab/vr-routeros:7.6     |
| Nokia SR Linux         | ghcr.io/nokia/srlinux:24.10.1 |
| Nokia SR OS            | vrnetlab/vr-sros:latest      |
| VyOS                   | ghcr.io/sysoleg/vyos-container |

* Cumulus VX, FRR, Linux, Nokia SR Linux, and VyOS images are automatically downloaded from public container registries.
* Build the BIRD and dnsmasq images with the **netlab clab build** command.
* Arista cEOS image has to be [downloaded and installed manually](ceos.md).
* Nokia SR OS and SR-SIM container images require a license; see also [vrnetlab instructions](https://containerlab.srlinux.dev/manual/vrnetlab/).
* Follow Cisco's documentation to install the IOS XRd container, making sure the container image name matches the one _netlab_ uses (alternatively, [change the default image name](default-device-image) for the IOS XRd container).
* Cisco 8000v containerlab image (once you manage to get it) has to be  [installed](https://containerlab.dev/manual/kinds/c8000/#getting-cisco-8000-containerlab-docker-images) with the **docker image load** command.

You can also use [vrnetlab](https://github.com/srl-labs/vrnetlab) to build VM-in-container images for Catalyst 8000v, Cisco CSR 1000v, Cisco IOSv, Cisco IOS on Linux (including layer-2 image), Nexus 9300v, IOS XR, Mikrotik RouterOS, Arista vEOS, Juniper vMX, vPTX, vQFX, and a few other devices.

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

### Interaction with iptables / netfilter

Linux bridges created by _netlab_ to support multi-access container networks are subject to the same security rules as all other Linux bridges on your server.

The `iptables` or [`nftables`](https://netfilter.org/projects/nftables/) policy rules do not apply to bridged traffic unless your server uses the **br_netfilter** module, which you can check with `lsmod|grep netfilter`. In a default setup of a typical Ubuntu server, the **br_netfilter** module would not impact IPv4 traffic but would block all IPv6 traffic. The default settings of other Linux distributions vary and may block all bridged traffic.

If your server uses the **br_netfilter** module, use `sudo sysctl net.bridge.bridge-nf-call-ip6tables=0` to turn off filtering of bridged IPv6 traffic (caution: this setting applies to the whole server). The `net.bridge.bridge-nf-call-iptables` parameter controls the filtering of bridged IPv4 traffic, and the `net.bridge.bridge-nf-call-arptables` parameter controls ARP. Alternatively, you could use `sudo nft add chain ip6 filter 'FORWARD { policy accept; }'` to change the default handling of IPv6 traffic from **drop all** to **permit all**.

```{warning}
Before changing the security settings of a server that is not a throwaway VM, please evaluate the broader impact of the changes you're planning to make.
```

If you want to troubleshoot the setup of `nftables` on your system, use `sudo nft list table ip filter` or `sudo nft list table ip6 filter` (both Containerlab and Libvirt insert their own rules to handle various forwarding scenarios).

Finally, `sudo dropwatch -l kas` ([Ubuntu installation guide](https://snapcraft.io/install/dropwatch/ubuntu)) may help shed some light on where packets are being dropped.

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

You can change a device management interface's IPv4/IPv6 address with the **mgmt.ipv4**/**mgmt.ipv6** node parameter *as long as the specified IPv4/IPv6 address is within the subnet specified in the **addressing.mgmt** pool*. However, it is recommended to use the **addressing.mgmt** pool **ipv4**/**ipv6**/**start** parameters to adjust the address range used for management IP addresses and rely on *netlab* to assign management IP addresses to containers based on [device node ID](node-augment).

(clab-network-mode)=
You can also set the **clab.network-mode** node parameter to *none* to disconnect a container from the management network. Use this setting in very large topologies (more than 1000 devices) to disconnect devices that don't run an SSH server from the management Linux bridge as a workaround for the *no more than 1024 interfaces per Linux bridge* limitation of the Linux kernel.

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
* Do not create device containers using the original _vrnetlab_ project. _netlab_ has been tested with the [vrnetlab fork](https://github.com/srl-labs/vrnetlab) supported by _containerlab_ (see [containerlab documentation](https://containerlab.dev/manual/vrnetlab/) for more details).
* Finally, _vrnetlab_ is an independent open-source project. If it fails to produce a working container image ([example](https://github.com/srl-labs/vrnetlab/issues/231)), please contact them.
```

(vrnetlab-images)=
### Image Names

The *vrnetlab* build process generates container tags based on the underlying VM image name. You will probably have to [change the default _netlab_ container image name](default-device-type) with the **‌defaults.devices._device_.clab.image** lab topology parameter ([more details](topo-defaults)) or with the `netlab defaults devices._device.clab.image=_new_image_name_` command.

(vrnetlab-usernames)=
### Usernames and Passwords

Most *vrnetlab* containers start with an unconfigured virtual machine and download the initial device configuration (including usernames and passwords) through the emulated VM console port. Recently, the *vrnetlab* project uses **admin** as the default username and **admin** (or **admin@123**) as the default password.

While we're trying to keep _netlab_ default settings in sync with _vrnetlab_ code, you could experience a mismatch between what *vrnetlab* configures on a network device and what *netlab*  thinks it will do. In that case, change the _netlab_ defaults with:

```
$ netlab defaults devices._device_.clab.group_vars.ansible_user=_username_
$ netlab defaults devices._device_.clab.group_vars.ansible_ssh_pass=_password_
```

You can also use another _vrnetlab_ detail: most containers can use `USERNAME` and `PASSWORD` environment variables to specify the username/password of the admin user. You can set these variables with the node **clab.env.USERNAME** and **clab.env.PASSWORD** parameters. For example, use these node settings to have a custom username and password for a Cisco IOSv device:

```
provider: clab

nodes:
  rtr:
    device: iosv
    ansible_user: Frodo
    ansible_ssh_pass: Baggins
    clab.env.USERNAME: Frodo
    clab.env.PASSWORD: Baggins
```

To change the default *vrnetlab* username/password for a device (not a single node), set the **defaults.devices._device_.clab.env.USERNAME** and **defaults.devices._device_.clab.env.PASSWORD** parameters, for example:

```
$ netlab defaults devices.iosv.clab.env.USERNAME=Frodo
$ netlab defaults devices.iosv.clab.env.PASSWORD=Baggins
```

Note: if you change these settings to non-standard values, you also have to adjust *netlab* Ansible variables:

```
$ netlab defaults devices.iosv.clab.group_vars.ansible_username=Frodo
$ netlab defaults devices.iosv.clab.group_vars.ansible_ssh_pass=Baggins
```

(vrnetlab-internal-net)=
### Internal Container Networking

The packaged container's architecture requires an internal network. The [*vrnetlab* fork](https://github.com/srl-labs/vrnetlab) supported by *containerlab* uses the IPv4 prefix 10.0.0.0/24 on that network, which clashes with the *netlab* loopback address pool. Fortunately, that fork also adds management VRF (and default route within the management VRF) to most device configurations, making the overlap between the *vrnetlab* internal subnet and the *netlab* loopback pool irrelevant. However, all VMs in *vrnetlab* containers will have the same IP and MAC address on the management interface, potentially confusing any network management system you might use with your lab.

Finally, if you're still experiencing connectivity problems or initial configuration failures with _vrnetlab_-based containers after rebuilding them with the [latest vrnetlab version](https://github.com/srl-labs/vrnetlab), add the following parameters to the lab configuration file to change the _netlab_ loopback addressing pool:

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

If your virtual machines take even longer to boot, increase the number of retries. You can set the **netlab_check_retries** node variable to increase the number of retries for an individual node or set the **defaults.devices._device_.clab.group_vars.netlab_check_retries** variable to increase the number of retries for a specific device (see also [](topo-defaults) and [](defaults-user-file))

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

_netlab_ tries to locate the Jinja2 templates in the device-specific **paths.templates.dirs** directories[^CFTD]; the template file name is the dictionary key (for example, `daemons`) with the `.j2` suffix.

[^CFTD]: See [](change-search-paths) for more details.

For example, with the default path settings, the user-specified `daemons.j2` template could be in the `templates/frr` subdirectory of:

* The lab topology directory
* The current directory
* The `~/.netlab` directory or
* The `/etc/netlab` directory.

```{tip}
The template search path is based on directories existing at the time you run **‌netlab create** or **‌netlab up**. Creating new directories after that point will not change the search path.
```

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
Ansible developers love to restructure stuff and move it into different directories. This functionality works with two implementations of **ipaddr** filters (tested on Ansible 2.10 and Ansible 7.4/ Ansible Core 2.14) but might break in the future. We're effectively playing whack-a-mole with Ansible developers.
```

[^HB]: Installing Ansible with Homebrew or into a separate virtual environment won't work -- _netlab_ has to be able to import Ansible modules

(clab-other-parameters)=
### Using Other Containerlab Node Parameters

You can also change these *containerlab* parameters:

* **clab.kind** -- [containerlab device kind](https://containerlab.dev/manual/kinds/). Set in the system defaults for all supported devices; use it only to specify the device type for [unknown devices](platform-unknown).
* **clab.type** to set node type (used by Nokia SR OS and Nokia SR Linux).
* **clab.dns** to [configure DNS servers and search domains](https://containerlab.dev/manual/nodes/#dns)
* **clab.env** to [set container environment](https://containerlab.dev/manual/nodes/#env) (used to [set interface names for Arista cEOS](https://containerlab.dev/manual/kinds/ceos/#additional-interface-naming-considerations))
* **clab.exec** to execute a list of commands after the container has started. If you want to start shell scripts, use **clab.binds** or **clab.config_templates** to make those scripts available to the container
* **clab.license** to configure a license file for those platforms that require one
* **clab.ports** to [map container ports to host ports](https://containerlab.dev/manual/nodes/#ports)
* **clab.cmd** to [change the command of a container image](https://containerlab.dev/manual/nodes/#cmd).
* **clab.startup-delay** to make certain node(s) [boot/start later than others](https://containerlab.dev/manual/nodes/#startup-delay) (amount in seconds)
* **clab.restart-policy** to set the [container restart policy](https://containerlab.dev/manual/nodes/#restart-policy)
* **clab.network-mode** to set the [network-mode](https://containerlab.dev/manual/nodes/#network-mode)

```{warning}
String values (for example, the command to execute specified in **clab.cmd**) are put into single quotes when written into the `clab.yml` containerlab configuration file. Ensure you're not using single quotes in your command line.
```

The complete list of supported Containerlab attributes is in the [system defaults](https://github.com/ipspace/netlab/blob/dev/netsim/providers/clab.yml#L22) and can be printed with the `netlab show defaults providers.clab.attributes` command.

To enable additional *containerlab* attributes in your lab topology, add them to the **defaults.providers.clab.attributes.node._keys** dictionary, for example:

```
provider: clab
defaults.providers.clab.attributes.node._keys:
  env:
  user: str
```

(clab-prefix)=
### Changing Container Names

By default, Netlab uses `clab` as the [containerlab naming prefix](https://containerlab.dev/manual/topo-def-file/#prefix),
which causes each container to be named `clab-{ topology name }-{ node name }`.

If you prefer plain node names (for example, to match DNS names used in your network), set the `defaults.providers.clab.lab_prefix`
to an empty string to remove both prefix strings, leaving just the node name as the container name.

Example:
```
netlab up topo.yml -s defaults.providers.clab.lab_prefix=""
```

```{warning}
Do not change the containerlab lab prefix if you're using the **multilab** plugin to run multiple labs on the same
server.
```

```{eval-rst}
.. toctree::
   :caption: Installing Container Images
   :maxdepth: 1
   :hidden:

   ceos.md
   linux.md
   netscaler.md
..
```
