# Contributing New Devices

Adding new devices to *netlab* shouldn't be too hard:

* [Figure out the device image to use](#device-images)
* [Create device settings file](dev-device-parameters) including [Ansible variables](#using-your-device-with-ansible-playbooks)
* Add [Ansible task lists](#configuring-the-device) to deploy and fetch device configurations
* Add [initial](#initial-device-configuration)- and [module-specific](#configuration-modules) configuration templates
* [Test and document your work](#test-your-changes)

[Adding support for a new virtualization provider](#adding-an-existing-device-to-a-new-virtualization-provider) to an existing device is even simpler.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Device Images

*netlab* supports three virtualization providers: *Vagrant* with *libvirt* and *Virtualbox*, and *containerlab* running Docker container images. 

If you can create a Vagrant box for the network device you want to use, or get a Docker container, it makes sense to proceed. Otherwise, yell at your vendor.

In this step, you should have a repeatable *build my box* recipe. It's perfectly understandable that one might have to register at a vendor web site to download a container or a Vagrant box, or the images used to build a Vagrant box. Asking the potential users to "_contact the account team_" is not[^1].

Please publish the recipe (it's OK to add it to *netlab* documentation under *install* directory) before proceeding. We want to have repeatable installation instructions ;)

[^1]: That was one of the reasons ArcOS was taken off the list of supported platforms.

(dev-device-parameters)=
## Device Parameters (System Settings)

After building a Vagrant box or a container, you have to integrate it with *netlab*. Start with *device name*:

* Device name should not be too long (up to 16 characters is still OK) and should contain alphanumeric characters, but no special characters or blanks.
* Check the [list of supported platforms](../platforms.md) for existing device names.

After you decided what *device name* to use, create `<device-name>.yml` file in `netsim/devices` directory. You'll use that file to store device parameters.

The device parameters will have to include ([more details](device-box.md#adding-new-device-settings)):

* Device **description** -- a short string describing the device
* Interface name template (**interface_name**), including `{ifindex}` to insert interface number.
* The number of the first interface (**ifindex_offset**) if it's different from 1. Sometimes the data plane interfaces start with zero, sometimes they start with 2 because the management interface is interface 1.
* Name of the management interface (**mgmt_if**) if it cannot be generated from the interface name template (some devices use `mgmt0` or similar). This is the interface Vagrant uses to connect to the device via SSH.
* Optional loopback interface name (**‌loopback_interface_name**), including `{ifindex}` to insert interface number.
* [Image name or box name](device-box.md#adding-new-device-settings) for every supported virtualization provider.

Here's the device parameters file for the dummy device (`none.yml`):

```
interface_name: eth{ifindex}
loopback_interface_name: Loopback{ifindex}
virtualbox:
  image: none
libvirt:
  image: none
clab:
  image: none
external:
  image: none
group_vars:
  ansible_connection: paramiko_ssh
  ansible_network_os: none
```

Some devices use different interface names for VMs and containers. Specify provider-specific parameters in `<provider>.parameter` settings. For example, Arista vEOS and cEOS have different management interface names:

```
interface_name: Ethernet{ifindex}
description: Arista vEOS
mgmt_if: Management1
loopback_interface_name: Loopback{ifindex}
clab:
  mgmt_if: Management0
```

Network OS containers could also use interface names that are different from the names of the underlying Linux interfaces. For example, Arista cEOS uses **EthernetX** in device configuration to refer to Linux interface **ethX**. To deal with such a device, specify Linux (container) interface name in **clab.interface.name** parameter:

```
interface_name: Ethernet{ifindex}
description: Arista vEOS
clab:
  interface:
    name: et{ifindex}
```

Finally, you can specify node attributes that are copied into node data (example: default device MTU) in **node** dictionary. If you want to specify provider-specific node parameters, use **_provider_.node** dictionary. For example, containers requires **clab.kind** attribute, and Arista cEOS requires an extra environment variable:

```
interface_name: Ethernet{ifindex}
description: Arista vEOS
clab:
  node:
    kind: ceos
    env:
      INTFTYPE: et
```

Device parameters file can also include numerous *features*. You'll find feature description in developer documentation for individual modules.

After creating the device parameters file, you'll be able to use your device in network topology and use **netlab create** command to create detailed device data and virtualization provider configuration file.

### Device Setting Inheritance

If you're adding a new device that is very similar to another device (example: Cisco IOSv/CSR1KV or Juniper vSRX/vMX/vPTX) use _device setting inheritance_:

* Specify new device as a subtype of an existing device with the **parent: _device_** setting.
* Specify modified device parameters in the new device's YAML configuration file.
* Set parameters that exist on the parent device but do not exist on the child device to `None` by specifying an empty value in the YAML file.

For example, Cisco CSR 1000v supports unnumbered IPv4 interfaces (IOSv does not) but does not support all VLAN modes that can be implemented in IOSv. It also uses different interface names and supports SR-MPLS and VXLAN.

The changes between the two devices are described with the following YAML data structure:

```yaml
description: Cisco CSR 1000v
parent: iosv
interface_name: GigabitEthernet{ifindex}
ifindex_offset: 2
virtualbox:
  image: cisco/csr1000v
group_vars:
  netlab_device_type: csr
node:
  min_mtu: 1500
features:
  initial:
    ipv4:
      unnumbered: true
  isis:
    unnumbered:
      ipv4: true
  sr: true
  vlan:
    model: switch
    svi_interface_name: BDI{vlan}
    mixed_trunk:
    native_routed:
    subif_name:
  vxlan: true
```
## Vagrant Template File

If you'll use a Vagrant box to start the network device as a VM, you have to add a template that will generate the part of *Vagrantfile* (or *containerlab* configuration file) describing your virtual machine. See `netsim/templates/provider/...` directories for more details.

## Using Your Device with Ansible Playbooks

If you want to configure your device with **[netlab initial](../netlab/initial.md)** or **[netlab config](../netlab/config.md)**, or connect to your device with **[netlab connect](../netlab/connect.md)**, you'll have to add Ansible variables that will be copied into **group_vars** part of Ansible inventory. Add those variables into the **group_vars** part of your device parameter file.

The Ansible variables should include:

* `ansible_connection` -- use **paramiko** for SSH access; you wouldn't want to be bothered with invalid SSH keys in a lab setup, and recent versions of Ansible became somewhat inconsistent in that regard.

* `ansible_network_os` -- must be specified if your device uses **network_cli** connection. 

* `netlab_device_type` or `ansible_network_os`[^DTP] is used to select the configuration task lists and templates used by **[netlab initial](../netlab/initial.md)**, **[netlab config](../netlab/config.md)** and **[netlab collect](../netlab/collect.md)** commands. Use `netlab_device_type` when you're creating different devices running the same operating system (example: Juniper vSRX and vMX both run Junos).

* `ansible_user` and `ansible_ssh_pass` must often be set to the default values included in the network device image.

[^DTP]: `netlab_device_type` takes precedence over `ansible_network_os`.

For example, here are the group variables for Cisco IOSv:

```
group_vars:
  ansible_user: vagrant
  ansible_ssh_pass: vagrant
  ansible_become_method: enable
  ansible_become_password: vagrant
  ansible_network_os: ios
  ansible_connection: network_cli
  netlab_device_type: ios
```

If you want to use the same device with multiple virtualization providers, you might have to specify provider-specific Ansible group variables in `<provider>.group_vars` key. For example, cEOS uses a different administrator username/password than the vEOS Vagrant box:

```
group_vars:
  ansible_user: vagrant
  ansible_ssh_pass: vagrant
  ansible_network_os: eos
  ansible_connection: network_cli
clab:
  interface:
    name: et{ifindex}
  node:
    kind: ceos
    env:
      INTFTYPE: et
  mgmt_if: Management0
  image: ceos:4.26.4M
  group_vars:
    ansible_user: admin
    ansible_ssh_pass: admin
    ansible_become: yes
    ansible_become_method: enable
```

## Configuring the Device

To configure your device (including initial device configuration), you'll have to create an Ansible task list that deploys configuration snippets onto your device. *netlab* merges configuration snippets with existing device configuration (instead of building a complete configuration and replacing it).

There are two ways to configure a devices:

* **Configuration templates**: you'll have to create a single Ansible *configuration deployment task list* that will deploy configuration templates. The configuration deployment task list has to be in the `netsim/ansible/tasks/deploy-config` and must match the `ansible_network_os` or `netlab_device_type` Ansible variable specified in device parameters file. [More details...](config/deploy.md)
* **Ansible modules** (or REST API): you'll have to create an Ansible task list for initial configuration and any other configuration module supported by the device. The task list has to be in the device-specific subdirectory of `netsim/ansible/templates/` directory; the subdirectory name must match the `ansible_network_os` or `netlab_device_type` Ansible variable specified in device parameters file. The task list name has to be `initial.yml` for initial configuration deployment or `<module>.yml` for individual configuration modules. [More details...](config/deploy.md)

You might want to implement configuration download to allow the lab users to save final device configurations with **collect-configs.ansible** playbook used by **[netlab collect](../netlab/collect.md)** command -- add a task list collecting the device configuration into the `netsim/ansible/tasks/fetch-config` directory.

## Initial Device Configuration

Most lab users will want to use **netlab initial** or **netlab up** command to build and deploy initial device configurations, from IP addressing to routing protocol configuration.

If decided to configure your devices with configuration templates, you have to create Jinja2 templates for initial device configuration and any configuration module you want to support.

Jinja2 templates that will generate IP addressing and LLDP configuration have to be within the `netsim/ansible/templates/initial` directory. The name of your template must match the `netlab_device_type` or `ansible_network_os` Ansible variable specified in device parameters file.

Jinja2 templates for individual configuration modules have to be in a subdirectory of the `netsim/ansible/templates` directory. The subdirectory name has to match the module name and the name of the template must match the `netlab_device_type` or `ansible_network_os` Ansible variable specified in device parameters file.

Use existing configuration templates and *[initial device configurations](../platforms.md#initial-device-configurations)* part of *[supported platforms](../platforms.md)* document to figure out what settings your templates should support. [More details...](config/initial.md)

## Configuration Modules

Similar to the initial device configuration, create templates supporting [individual configuration modules](../module-reference.md) in module-specific subdirectories of the `templates` directory.

Use existing configuration templates and module description to figure out which settings your templates should support.

For every configuration module you add, update the device's `features` dictionary to indicate that the configuration module is supported by the network device. When a configuration module has no extra options (or your device doesn't support them), simply add `_module_: True` line. Explore existing device YAML definitions for more details. For example, this is the definition declaring that Cisco IOSv supports BFD (with no extra options) and BGP with a number BGP-specific features:

```
features:
  bfd: true
  bgp:
    local_as: true
    vrf_local_as: true
    local_as_ibgp: true
    activate_af: true
```

The list of supported devices is used by the **netlab create** command to ensure the final lab topology doesn't contain unsupported/unimplemented module/device combinations.

## Adding an Existing Device to a New Virtualization Provider

To add a device that is already supported by *netlab* to a new virtualization environment follow these steps:

* Get or build a Vagrant box or container image.
* Add the [image/box/container name](device-box.md#adding-new-device-settings) for the new virtualization provider to device parameters file.
* Add device-specific virtualization provider configuration template to provider-specific subdirectory of `netsim/templates/provider` directory. Use existing templates to figure out what exactly needs to be done.
* You might need to add provider-specific device settings to device parameters file. See the above Arista cEOS examples for more details.

**Notes**
* The **node** dictionary within provider-specific device settings is copied directly into node data under provider key. For example, **clab.node**  Arista cEOS setting (from `netsim/devices/eos.yml`) is copied into **nodes.s1.clab** assuming S1 is an EOS device and you're using *clab* provider.
* Other provider-specific device settings overwrite global device settings.

## Test Your Changes

* Create a simple topology using your new device type in the `tests/integration` directory.
* Create Ansible inventory and Vagrantfile with `netlab create`
* Start your virtual lab
* Perform initial device configuration with `netlab initial`
* Log into the device and verify interface state and interface IP addresses

## Final Steps

* Fix the documentation (at least **install.md** and **platforms.md** documents).
* Make sure you created at least one test topology in `tests/integration/platform` directory.
* Submit a pull request against the **dev** branch.

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Implementation Notes

   config/deploy.md
   config/initial.md
   config/ospf.md
   config/bfd.md
   config/vlan.md
   config/vrf.md
```
