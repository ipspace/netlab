# Adding New Non-Configurable Device

Adding a new non-configurable device is almost as easy as [adding a virtualization provider for an existing device](device-platform.md).

Here's what you have to do:

* Choose a short name for the new device type (examples: *ios*, *eos*, *cumulus*...)
* Select one or more virtualization providers you want to work with.
* Build a Vagrant box from whatever image your vendor supplies. It's not as hard as it sounds, there are [tons of recipes on codingpackets.com](https://codingpackets.com/blog/tag/#vagrant). If you want to build a container to use with *containerlab*, please refer to [their documentation](https://containerlab.srlinux.dev/).
* Document the process in a blog post or GitHub gist.
* Add device parameter file `<device>.yml` to `netsim/devices` directory (see the next section for details).
* Update [Supported Platforms](supported-platforms) and [box](libvirt-build-boxes) or [container](clab-images) building documentation.
* Hopefully [Submit a PR](guidelines.md)
* Enjoy!

## Adding New Device Settings

* Every device parameter file must have a **description** -- a short string describing the device
* For every supported virtualization provider, define device box (or container) to use with **image** parameter within the **_provider_** dictionary (example **libvirt.image**).
* Define interface names as used by the new device with **interface_name**, **mgmt_if** and optionally **ifindex_offset** ([more details](dev-device-parameters))
* Add **group_vars** dictionary with Ansible variables specific to the new device. Set at least the **ansible_connection** and **ansible_network_os** variables. **ansible_user** and **ansible_ssh_pass** are highly recommended unless you're using *docker* connection type. The group variables are required even if you don't plan to implement a configurable device; they are used by **netlab connect** command to figure out how to connect to a device.

Example: Mikrotik RouterOS

```
interface_name: ether%d
mgmt_if: ether1
ifindex_offset: 2
libvirt:
  image: mikrotik/chr
group_vars:
  ansible_network_os: routeros
  ansible_connection: network_cli
  ansible_user: admin
  ansible_ssh_pass: admin
```
