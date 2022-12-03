# Adding New Virtualization Provider for an Existing Device

If you want to run a network device on a virtualization provider that is not yet supported by *netlab* (example: Fortinet firewall on VirtualBox as of December 2020), you came to the right place.

Here's what you have to do:

* Build a Vagrant box from whatever image your vendor supplies. It's not as hard as it sounds, there are [tons of recipes on codingpackets.com](https://codingpackets.com/blog/tag/#vagrant). If you want to build a container to use with *containerlab*, please refer to [their documentation](https://containerlab.srlinux.dev/).
* Document the process in a blog post or GitHub gist.
* Modify the *netlab* settings in `netsim/topology-defaults.yml`
* Update [Supported Platforms](../platforms.md) and box building documentation ([libvirt](../labs/libvirt.md#building-your-own-boxes), [VirtualBox](../labs/virtualbox.md#creating-vagrant-boxes))
* Hopefully [Submit a PR](guidelines.md)
* Enjoy!

## Adding a Box Name to Topology Defaults

* Find your device settings within **devices** dictionary
* Add a new key *provider* key for the target device (valid keys are `libvirt`, `virtualbox` or `clab`). Add **image** parameter under the *provider* key. Its value is the expected Vagrant box name or Docker container.

Example:

```
devices:
  routeros:
    interface_name: ether%d
    virtualbox:
      image: mikrotik/chr
```

Recommended:

* Use standard Docker Hub container names (which can include the version number in *tag* field)
* If you need a version number for a Vagrant image downloaded from Vagrant Cloud, use *user/image:version* format (example: `CumulusCommunity/cumulus-vx:4.3.0`)

## Changing Provider-Specific Device Settings

You can change default device settings for a specific virtualization provider (example: interface names on Arista cEOS) within **devices** part of virtualization provider settings.

There are four types of settings you can change:

**Default settings** (easy) -- **devices._type_._provider_** settings are merged with the **devices._type_** defaults. 

**Example:** Change management interface name and container image on Arista cEOS:

```
devices:
  eos:
    clab:
      mgmt_if: Management0
      image: ceos:4.25.1F
```

**Ansible group variables** (easy) -- values specified in **group_vars** section of device-and-provider-specific settings overwrite the device defaults. 

Example: Change Ansible connection for a Cumulus VX container:

```
devices:
  cumulus:
    clab:
      group_vars:
        ansible_connection: docker
        ansible_user: root
```

**Node parameters** (manageable)-- the **node** dictionary within provider-specific device settings is copied into node data under _provider_ key.

Example: *containerlab* needs a *device kind* setting in its configuration file. The configuration file template uses **clab.kind** value within node data to set that parameter, so we need a mechanism to set **clab.kind** value for every node. 

Solution: use **node** dictionary within **devices._device_.clab** settings:

```
devices:
  srlinux:
    clab:
      image: ghcr.io/nokia/srlinux
      node:
        kind: srl
        type: ixrd2
```

**Interface names** (mind-boggling). Interface names used by the network device might differ from the interface names used by virtualization provider (example: Arista cEOS on *containerlab*).

Solution: set **interface.name** in provider-specific device settings. Whenever those settings include **interface.name** value, the link interface data and node interfaces data includes **_provider_.name** value for every interface. That value can then be used in configuration templates.

**Example:** Arista cEOS containerlab settings

```
devices:
  eos:
    interface_name: Ethernet%d
    mgmt_if: Management1
    clab:
      interface:
        name: et%d
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

**Example**: Part of containerlab configuration template

```
...
  links:
{% for l in links %}
  - endpoints:
{%   for n in nodes.values() %}
{%     for nl in n.interfaces if nl.linkindex == l.linkindex %}
{%       set clab = nl.clab|default({}) %}
    - "{{ n.name }}:{{ clab.name|default(nl.ifname) }}"
{%     endfor %}
{%   endfor %}
{% endfor %}
```
