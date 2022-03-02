# Contributing New Devices

Adding new devices to netsim-tools shouldn't be too hard:

* [Figure out the device image to use](#device-images)
* [Modify system settings](#system-settings) including [Ansible variables](#using-your-device-with-ansible-playbooks)
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

*netsim-tools* supports three virtualization providers: *Vagrant* with *libvirt* and *Virtualbox*, and *containerlab* running Docker container images. 

If you can create a Vagrant box for the network device you want to use, or get a Docker container, it makes sense to proceed. Otherwise, yell at your vendor.

In this step, you should have a repeatable *build my box* recipe. It's perfectly understandable that one might have to register at a vendor web site to download a container or a Vagrant box, or the images used to build a Vagrant box. Asking the potential users to "_contact the account team_" is not[^1].

Please publish the recipe (it's OK to add it to *netsim-tools* documentation under *install* directory) before proceeding. We want to have repeatable installation instructions ;)

[^1]: That was one of the reasons ArcOS was taken off the list of supported platforms.

## System Settings

After building a Vagrant box or a container, you have to integrate it with *netsim-tools*. You'll need

* A template that will generate the part of *Vagrantfile* (or *containerlab* configuration file) describing your virtual machine. See `netsim/templates/provider/...` directories for details.
* Device parameters within the **devices** section of `netsim/topology-defaults.yml`.

The device parameters will have to include ([more details](device-box.md#adding-new-device-settings)):

* Interface name template (**interface_name**), including `%d` to insert interface number.
* The number of the first interface (**ifindex_offset**) if it's different from 1. Sometimes the data plane interfaces start with zero, sometimes they start with 2 because the management interface is interface 1.
* Name of the management interface (**mgmt_if**) if it cannot be generated from the interface name template (some devices use `mgmt0` or similar). This is the interface Vagrant uses to connect to the device via SSH.
* [Image name or box name](device-box.md#adding-new-device-settings) for every supported virtualization provider.

After adding the device parameters into `netsim/topology-defaults.yml`, you'll be able to use your device in network topology and use **netlab create** command to create detailed device data and virtualization provider configuration file.

## Using Your Device with Ansible Playbooks

If you want to configure your device with **[netlab initial](../netlab/initial.md)** or **[netlab config](../netlab/config.md)**, or connect to your device with **[netlab connect](../netlab/connect.md)**, you'll have to add Ansible variables that will be copied into **group_vars** part of Ansible inventory into the **group_vars** part of your device settings.

The Ansible variables should include:

* `ansible_connection` -- use **paramiko** for SSH access; you wouldn't want to be bothered with invalid SSH keys in a lab setup, and recent versions of Ansible became somewhat inconsistent in that regard.

* `ansible_network_os` -- must be specified if your device uses **network_cli** connection. 

* `netlab_device_type` or `ansible_network_os`[^DTP] is used to select the configuration task lists and templates used by **[netlab initial](../netlab/initial.md)**, **[netlab config](../netlab/config.md)** and **[netlab collect](../netlab/collect.md)** commands. Use `netlab_device_type` when you're creating different devices running the same operating system (example: ExaBGP daemon on Linux).

* `ansible_user` and `ansible_ssh_pass` must often be set to the default values included in the network device image.

[^DTP]: `netlab_device_type` takes precedence over `ansible_network_is`.

If you want to use the same device with multiple virtualization providers, you might have to specify provider-specific Ansible group variables (see **providers.clab.devices.eos** settings for details).

## Configuring the Device

To configure your device (including initial device configuration), you'll have to create an Ansible task list that deploys configuration snippets onto your device. *netsim-tools* rely on merging configuration snippets with existing device configuration, not replacing it.

There are two ways to configure a devices:

* **Configuration templates**: you'll have to create a single Ansible *configuration deployment task list* that will deploy configuration templates. The configuration deployment task list has to be in the `netsim/ansible/tasks/deploy-config` and must match the `ansible_network_os` setting from `netsim/topology-defaults.yml`. [More details...](config/deploy.md)
* **Ansible modules** (or REST API): you'll have to create an Ansible task list for initial configuration and any other configuration module supported by the device. The task list has to be in the device-specific subdirectory of `netsim/ansible/templates/` directory; the subdirectory name must match the `ansible_network_os` setting from `netsim/topology-defaults.yml`. The task list name has to be `initial.yml` for initial configuration deployment or `module.yml` for individual configuration modules (replace *module* with the module name). [More details...](config/deploy.md)

You might want to implement configuration download to allow the lab users to save final device configurations with **collect-configs.ansible** playbook used by **[netlab collect](../netlab/collect.md)** command -- add a task list collecting the device configuration into the `netsim/ansible/tasks/fetch-config` directory.

## Initial Device Configuration

Most lab users will want to use **netlab initial** or **netlab up** command to build and deploy initial device configurations, from IP addressing to routing protocol configuration.

If decided to configure your devices with configuration templates, you have to create Jinja2 templates for initial device configuration and any configuration module you want to support.

Jinja2 templates that will generate IP addressing and LLDP configuration have to be within the `netsim/ansible/templates/initial` directory. The name of your template must match the `netlab_device_type` or `ansible_network_os` value from `netsim/topology-defaults.yml`.

Jinja2 templates for individual configuration modules have to be in a subdirectory of the `netsim/ansible/templates` directory. The subdirectory name has to match the module name and the name of the template must match the `netlab_device_type` or `ansible_network_os` value from `netsim/topology-defaults.yml`.

Use existing configuration templates and *[initial device configurations](../platforms.md#initial-device-configurations)* part of *[supported platforms](../platforms.md)* document to figure out what settings your templates should support. [More details...](config/initial.md)

## Configuration Modules

Similar to the initial device configuration, create templates supporting [individual configuration modules](../module-reference.md) in module-specific subdirectories of the `templates` directory.

Use existing configuration templates and module description to figure out which settings your templates should support.

For every configuration module you add, update the module's `supported_on` list in `netsim/topology-defaults.yml` to indicate that the configuration module is supported by the network device. The list of supported devices is used by the **netsim create** command to ensure the final lab topology doesn't contain unsupported/unimplemented module/device combinations.

## Adding an Existing Device to a New Virtualization Provider

To add a device that is already supported by *netsim-tools* to a new virtualization environment follow these steps:

* Get or build a Vagrant box or container image.
* Add the [image/box/container name](device-box.md#adding-new-device-settings) for the new virtualization provider to system settings.
* Add device-specific virtualization provider configuration to provider-specific subdirectory of `netsim/templates/provider` directory. Use existing templates to figure out what exactly needs to be done.
* You might need to add provider-specific device settings to system defaults (`netsim/topology-defaults.yml`). See **devices.eos.clab** settings for details.

**Notes**
* The **node** dictionary within provider-specific device settings is copied directly into node data under provider key (example: **devices.eos.clab.node**  system setting is copied into **nodes.s1.clab** assuming S1 is an EOS device and you're using *clab* provider).
* Other provider-specific device settings overwrite global device settings.

## Test Your Changes

* Create a simple topology using your new device type in the `tests/integration` directory.
* Create Ansible inventory and Vagrantfile with `netlab create`
* Start your virtual lab
* Perform initial device configuration with `netlab initial`
* Log into the device and verify interface state and interface IP addresses

## Final Steps

* Fix the documentation (at least **install.md** and **platforms.md** documents).
* Make sure you created at least one test topology in `tests/integration` directory.
* Submit a pull request against the **dev** branch.

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Implementation Notes

   config/deploy.md
   config/initial.md
   config/ospf.md
   config/bfd.md
```
