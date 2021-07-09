# Contributing New Devices

Adding new devices to netsim-tools shouldn't be too hard:

* [Figure out the device image to use](#device-images)
* [Modify system settings](#system-settings) including [Ansible variables](#using-your-device-with-ansible-playbooks)
* Add [Ansible task lists](#configuring-the-device) to deploy and fetch device configurations
* Add [initial](#initial-device-configuration)- and [module-specific](#configuration-modules) configuration templates
* [Test and document your work](#test-your-changes)

[Adding support for a new virtualization provider](#adding-an-existing-device-to-a-new-virtualization-provider) to an existing device is even simpler.

## Device Images

*netsim-tools* supports three virtualization providers: *Vagrant* with *libvirt* and *Virtualbox*, and *containerlab* running Docker container images. 

If you can create a Vagrant box for the network device you want to use, or get a Docker container, it makes sense to proceed. Otherwise, yell at your vendor.

In this step, you should have a repeatable *build my box* recipe. It's perfectly understandable that one might have to register at a vendor web site to download a container or a Vagrant box, or the images used to build a Vagrant box. Asking the potential users to "_contact the account team_" is not[^1].

[^1]: ArcOS was a not-to-be-repeated one-off.

## System Settings

After building a Vagrant box or a container, you have to integrate it with *netsim-tools*. You'll need

* A template that will generate the part of *Vagrantfile* (or *containerlab* configuration file) describing your virtual machine. See `netsim/templates/provider/...` directories for details.
* Device parameters within the **devices** section of `netsim/topology-defaults.yml`.

The device parameters will have to include:

* Interface name template (**interface_name**), including `%d` to insert interface number.
* The number of the first interface (**ifindex_offset**) if it's different from 1. Sometimes the data plane interfaces start with zero, sometimes they start with 2 because the management interface is interface 1.
* Name of the management interface (**mgmt_if**) if it cannot be generated from the interface name template (some devices use `mgmt0` or similar). This is the interface Vagrant uses to connect to the device via SSH.
* Image name or box name for every supported virtualization provider (**image**).

After adding the device parameters into `netsim/topology-defaults.yml`, you'll be able to use your device in network topology and use **netlab create** command to create detailed device data and virtualization provider configuration file.

## Using Your Device with Ansible Playbooks

If you want to configure your device with **[netlab initial](netlab/initial.md)** or **[netlab config](netlab/config.md)**, or connect to your device with **[netlab connect](netlab/connect.md)**, you'll have to add Ansible variables that will be copied into **group_vars** part of Ansible inventory into the **group_vars** part of your device settings.

The Ansible variables should include:

* `ansible_connection` -- use **paramiko** for SSH access; you wouldn't want to be bothered with invalid SSH keys in a lab setup, and recent versions of Ansible became somewhat inconsistent in that regard.

* `ansible_network_os` -- must be specified even if your device does not use **network_cli** connection. The value of this variable is used to select the configuration templates in the **initial-config.ansible** playbook used by **[netlab initial](netlab/initial.md)** command.

* `ansible_user` and `ansible_ssh_pass` must often be set to the default values included in the network device image.

If you want to use the same device with multiple virtualization providers, you might have to specify provider-specific Ansible group variables (see **providers.clab.devices.eos** settings for details).

## Configuring the Device

To configure your device (including initial device configuration), you'll have to create an Ansible task list that deploys configuration snippets onto your device. *netsim-tools* rely on merging configuration snippets with existing device configuration, not replacing it.

The configuration deployment task list has to be in the `netsim/ansible/tasks/deploy-config` and must match the `ansible_network_os` setting from `netsim/topology-defaults.yml`.

You might want to implement configuration download to allow the lab users to save final device configurations with **collect-configs.ansible** playbook used by **[netlab collect](netlab/collect.md)** command -- add a task list collecting the device configuration into the `netsim/ansible/tasks/fetch-config` directory.

## Initial Device Configuration

Most lab users will want to use **netlab initial** script to build and deploy initial device configurations, from IP addressing to routing protocol configuration.

Create Jinja2 templates that will generate IP addressing and LLDP configuration within the `netsim/ansible/templates/initial` directory. The name of your template must match the `ansible_network_os` value from `netsim/topology-defaults.yml`.

Use existing configuration templates and *[initial device configurations](platforms.md#initial-device-configurations)* part of *[supported platforms](platforms.md)* document to figure out what settings your templates should support.

## Configuration Modules

Similar to the initial device configuration, create templates supporting [individual configuration modules](module-reference.md) in module-specific subdirectories of the `templates` directory.

Use existing configuration templates and module description to figure out which settings your templates should support.

For every configuration module you add, update the module's `supported_on` list in `netsim/topology-defaults.yml` to indicate that the configuration module is supported by the network device. The list of supported devices is used by the **netsim create** command to ensure the final lab topology doesn't contain unsupported/unimplemented module/device combinations.

## Adding an Existing Device to a New Virtualization Provider

To add a device that is already supported by *netsim-tools* to a new virtualization environment follow these steps:

* Get or build a Vagrant box or container image.
* Add device-specific virtualization provider configuration to provider-specific subdirectory of `netsim/templates/provider` directory. Use existing templates to figure out what exactly needs to be done.
* You might need to add provider-specific device settings to system defaults (`netsim/topology-defaults.yml`). See **providers.clab.devices.eos** settings for details.

**Notes**
* Provider-specific device settings starting with **provider_** prefix are copied directly into node data (removing **provider_** prefix while doing that).
* Other provider-specific device settings overwrite global device settings.

## Test Your Changes

* Create a simple topology using your new device type in the `tests/integration` directory
* Create Ansible inventory and Vagrantfile with `netlab create`
* Start your virtual lab
* Perform initial device configuration with `netlab initial`
* Log into the device and verify interface state and interface IP addresses

## Final Steps

* Fix the documentation (at least **install.md** and **platforms.md** documents)
* Submit a pull request against the latest development (**dev_xxx**) branch.
