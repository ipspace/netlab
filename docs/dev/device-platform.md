# Adding New Virtualization Provider for an Existing Device

If you want to run a network device on a virtualization provider that is not yet supported by *netsim-tools* (example: Fortinet firewall on VirtualBox as of December 2020), you came to the right place.

Here's what you have to do:

* Build a Vagrant box from whatever image your vendor supplies. It's not as hard as it sounds, there are [tons of recipes on codingpackets.com](https://codingpackets.com/blog/tag/vagrant/). If you want to build a container to use with *containerlab*, please refer to [their documentation](https://containerlab.srlinux.dev/).
* Document the process in a blog post or GitHub gist.
* Modify the *netsim-tools* settings in netsim/topology-defaults.yml`
* Update [Supported Platforms](../platforms.md) and box building documentation ([libvirt](../labs/libvirt.md#building-your-own-boxes), [VirtualBox](../labs/virtualbox.md#creating-vagrant-boxes))
* Hopefully [Submit a PR](guidelines.md)
* Enjoy!

## Adding a Box Name to Topology Defaults

* Find your device settings within **devices** dictionary
* Add a new key (provider name -- `libvirt`, `virtualbox` or `clab`) into **image** dictionary. Its value is the expected Vagrant box name or Docker container.

Recommended:

* Use standard Docker Hub container names (which can include the version number in *tag* field)
* If you need a version number for a Vagrant image downloaded from Vagrant Cloud, use *user/image:version* format (example: `CumulusCommunity/cumulus-vx:4.3.0`)

## Changing Provider-Specific Device Settings

You can change default device settings for a specific virtualization provider (example: interface names on Arista cEOS) within **devices** part of virtualization provider settings.

There are four types of settings you can change:

**Default settings** (easy) -- ***provider*.devices** and ***provider*.addressing** settings are merged with the **devices** and **addressing** defaults. 

Example: Change management interface name on Arista cEOS:

```
providers:
  clab:
    devices:
      eos:
        mgmt_if: Management0
        image:
          clab: ceos:4.25.1F
```

**Ansible group variables** (easy) -- values specified in **group_vars** section of device-and-provider-specific settings overwrite the device defaults. 

Example: Change Ansible connection for a Cumulus VX container:

```
providers:
  clab:
    devices:
      cumulus:
        group_vars:
          ansible_connection: docker
          ansible_user: root
```

**Node parameters** (manageable)-- provider-specific device settings starting with **provider_** are copied to node data.

Example: *containerlab* needs a *device kind* setting in its configuration file. The configuration file template uses **kind** value within node data to set that parameter, so we need a mechanism to set **kind** value for every node. 

Solution: use **provider_kind** parameter for every device supported on *containerlab*:

```
providers:
  clab:
    devices:
      eos:
        mgmt_if: Management0
        provider_kind: ceos
        image:
          clab: ceos:4.25.1F
```

**Interface names** (mind-boggling). Interface names used by the network device might differ from the interface names used by virtualization provider (example: Arista cEOS on *containerlab*).

Solution: use **provider_interface_name** in provider-specific device settings. Whenever those settings include **provider_interface_name**, the link data structure includes **provider_ifname** value for every node attached to that link. The **provider_ifname** value can then be used in configuration file templates.

```
providers:
  clab:
    devices:
      eos:
        provider_interface_name: eth%d
```
