# Virtualization Providers

*netlab* uses third-party orchestration and virtualization tools to create, start, stop, and destroy virtual labs. It supports the following virtualization providers:

* **[libvirt](labs/libvirt.md)** -- *libvirt* virtualization abstraction layer (tested on top of KVM/QEMU on Ubuntu) orchestrated with Vagrant using *vagrant-libvirt* Vagrant plugin.
* **[clab](labs/clab.md)** -- Docker containers (tested on Ubuntu) orchestrated with *containerlab*.
* **[virtualbox](labs/virtualbox.md)** -- VirtualBox virtualization orchestrated with Vagrant using built-in VirtualBox plugin.
* **external** -- meta-provider you can use to configure hardware devices.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Combining Virtualization Providers

You can use multiple virtualization providers within the same lab topology. One of them is the _primary_ provider specified in the **provider** topology attribute, other(s) are _secondary_ providers specified with **provider** attribute on individual nodes.

```{warning}
You MUST use **[netlab up](netlab/up.md)** to start the lab and **[netlab down](netlab/down.md)** to stop the lab when using a combination of virtualization providers. _netlab_ has to do some heavy lifting behind the scenes to make it work.
```

For example, you could have a topology that implements routers as virtual machines (using _libvirt_ primary provider) and end hosts as containers (using _clab_ secondary provider):

```
provider: libvirt

nodes:
  h1:
    device: linux
    provider: clab
  r1:
    device: iosv
    module: [ ospf ]
  r2:
    device: iosv
    module: [ ospf ]
  h2:
    device: linux
    provider: clab

links:
- h1-r1
- r1-r2
- r2-h2
```

_netlab_ supports the following combinations of primary/secondary virtualization providers:

| Primary provider | Secondary provider(s) |
| ---------------- | --------------------- |
| libvirt          |  clab                 |

(external-virtualization-provider)=
## Using External Provider

You can use *netlab* to create addressing plans and device configurations for a hardware lab **as long as the topology file contains an accurate description of the hardware lab**. 

You can use any device supported by *netlab* with the **external** provider, but you might have to customize the lab topology file -- hardware devices might use:

* Preconfigured management IPv4/IPv6 addresses
* Interface names different from names used by virtual devices
* Different access credentials.

### Static Management IP Addresses

To specify a static management IPv4/IPv6 address for a lab device, set **mgmt.ipv4** or **mgmt.ipv6** node parameter. To set the management interface name, use **mgmt.ifname** parameter:

* You SHOULD set static management IPv4/IPv6 addresses for all devices in your hardware lab.
* You don't have to set the management interface names for most devices -- management interfaces are usually not configured during the initial device configuration process.

Example:

```
nodes:
  r1:
    mgmt.ipv4: 10.20.30.50
    mgmt.ifname: ether9
```

### Setting Interface Names

*netlab* creates device interface names based on the naming conventions used by virtual devices. If your hardware devices use the same interface names, **and if your lab topology lists links in just the right order** to generate the desired device interface names, you don't have to specify interface names in the lab topology. In most other cases, you REALLY SHOULD specify interface names using **ifname** interface (node-to-link connection) attribute.

Example:

```
links:
- r1:
    ifname: sfp-1
  r2:
    ifname: GigabitEthernet0/3
```

### Access Credentials

It's STRONGLY RECOMMENDED to use usernames and passwords hardcoded into *netlab* with hardware devices (see **devices** section of [topology-defaults.yml](https://github.com/ipspace/netlab/blob/master/netsim/topology-defaults.yml) for more details).

Access credentials are stored in Ansible group variables and derived from the **group_vars** section of device defaults.
To change access credentials for a device type, set the `defaults.devices.<device>.group_vars.ansible_user` and `defaults.devices.<device>.group_vars.ansible_ssh_pass` parameters.

You can also change the access credentials for individual nodes -- set **ansible_user** or **ansible_ssh_pass** node parameters, for example:

```
nodes:
  r1:
    mgmt.ipv4: 10.20.30.50
    mgmt.ifname: ether9
    ansible_user: Vagrant
    ansible_ssh_pass: "vagrant!"
```

```eval_rst
.. toctree::
   :caption: More Information on Virtualization Providers
   :maxdepth: 1

   labs/libvirt.md
   labs/virtualbox.md
   labs/clab.md
```
