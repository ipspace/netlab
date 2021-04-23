# Contributing New Devices

Adding new devices to netsim-tools shouldn't be too hard:

* Figure out the device image to use
* Modify system settings
* Add Ansible task lists to deploy and fetch device configurations
* Add configuration templates.

You don't have to go all the way. Here are the steps you could follow:

* To use a network device in **create-topology** script, add device-specific settings to **devices** section of `netsim/topology-defaults.yml` configuration file.
* To use a network device with a specific virtualization provider, add device-specific template to corresponding `netsim/templates/provider` directory.
* To use a network device with netsim-tools Ansible playbooks, add device-specific task lists to `ansible/deploy-config` and `ansible/fetch-config` directories.
* Deploying initial device configuration with **initial-config.ansible** requires device-specific task list in `ansible/deploy-config` and device configuration template in `templates/initial` directory.
* To use a specific configuration module with a network device, follow the requirements for initial device configurations, and add module-specific configuration template to `templates/module` directory.

## Adding a Existing Device to a New Virtualization Provider

To add a device that is already supported by netsim-tools to a new virtualization environment follow these steps:

* Get or build a Vagrant box or container image.
* Add device-specific configuration to provider-specific subdirectory of `netsim/templates/vagrant/provider` directory. Use existing templates to figure out what exactly needs to be done.
* You might need to add provider-specific device settings to system defaults (`netsim/topology-defaults.yml`). See **providers.clab.devices.eos** settings for details.

**Notes**
* Provider-specific device settings starting with **provider_** prefix are copied directly into node data (removing **provider_** prefix while doing that).
* Other provider-specific device settings overwrite global device settings.

## Adding a New Device Type

To add a new device to netsim-tools, add device-specific settings to **devices** part of system settings (in `netsim/topology-defaults.yml` file). You should specify at least:

* Interface name template (**interface_name**)
* Device image used for all supported virtualization providers (**image**)

You might also specify:

* Management interface name (**mgmt_if**)
* Interface number of the first usable interface (**ifindex_offset**)

Next, [add virtualization provider settings](#adding-a-existing-device-to-a-new-virtualization-provider) for your device.

To use your new device with Ansible playbooks:

* In **devices** part of system settings (`netsim/topology-defaults.yml` file), specify Ansible group variables (**group_vars**), including **ansible_user**, **ansible_ssh_pass** (if needed), **ansible_network_os** and **ansible_connection**. If you want to use the same device with multiple virtualization providers, you might have to specify provider-specific Ansible group variables (see **providers.clab.devices.eos** settings for details).
* Add configuration deployment task list using device-specific Ansible configuration module to `ansible/deploy-config` directory. The name of your task list must match the **ansible_network_os** value you specified for your device.
* Add configuration retrieval task list using device-specific Ansible module(s) to `ansible/fetch-config` directory. The name of your task list must match the **ansible_network_os** value you specified for your device.
* Add initial device configuration template to `templates/initial` directory. The template name must match **ansible_network_os** value specified in system settings.

* Optional: add device configuration templates for individual modules. 

To add configuration module support, add device configuration template to corresponding `templates/module` directory. Use existing configuration templates to figure out which settings your templates should support. For example, to add OSPF support for Cumulus VX, create NCLU configuration template in `templates/ospf/cumulus.j2` (assuming you set the **ansible_network_os** value to *cumulus*).

## Test Your Changes

* Create a simple topology using your new device type
* Create Ansible inventory and Vagrantfile with `create-topology -p -i`
* Start your virtual lab
* Perform initial device configuration with `initial-config.ansible`
* Log into the device and verify interface state and interface IP addresses

Final steps:

* Fix the documentation (at least install.md and platforms.md)
* Submit a pull request ;)
