(dev-config-netmiko)=
# Deploying Device Configurations with Netmiko

_netlab_ can use the [netmiko](https://github.com/ktbyers/netmiko) library instead of Ansible playbooks to deploy device configurations. The *netmiko* configuration method opens an SSH session to the device, enters the configuration mode, and sends the rendered configuration snippets to the device line-by-line. It's much faster than an Ansible playbook, as it does not have to start a separate Ansible process (and a separate SSH session) for every configuration snippet.

This document describes how the *netmiko* configuration method works and which device settings you have to define to use it. The *netmiko* configuration method is currently available on these platforms:

{.table-wrap}
| Device | Device<br>settings | *netmiko*<br>device type | Default configuration method |
|--------|--------------------|------------------------|------------------------------|
| Arista EOS | `eos.yml` | `arista_eos` | Ansible |
| Cisco IOS/IOS XE[^IOS] | `ios.yml` | `cisco_ios` | Ansible |
| Cisco Nexus OS | `nxos.yml` | `cisco_nxos` | **netmiko** |
| Cisco IOS XR[^XR] | `xr.yml` | `cisco_xr` | **netmiko** |
| IP Infusion OcNOS | `ocnos.yml` | `ipinfusion_ocnos` | **netmiko** |

[^IOS]: Including all devices using **ios** as their parent device: Cisco IOSv, IOSvL2, CSR 1000v, Catalyst 8000v, IOL, and IOL L2 image.

[^XR]: Including all devices using **xr** as their parent device: IOS XRv, IOS XRd, and Cisco 8000v.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Selecting the Configuration Method

The configuration method used by a lab device is specified in the **netlab_config_mode** device group variable or node parameter. _netlab_ uses *netmiko* to configure a node when the value of that variable is `netmiko`.

The **netlab_config_mode** value must be one of the values listed in the **features.initial.config_mode** device feature. That list could be provider-specific. For example, Cisco IOS devices can use the *netmiko* configuration method with any virtualization provider, and the *startup* configuration method with *containerlab*:

```
features:
  initial:
    config_mode: [ netmiko ]
...
clab:
  features:
    initial:
      config_mode: [ startup, netmiko ]
```

To make *netmiko* the default configuration method for a device, set the **group_vars.netlab_config_mode** device parameter. For example, Cisco Nexus OS uses this definition in the `nxos.yml` device settings file:

```
group_vars:
  netlab_config_mode: netmiko
```

On devices where *netmiko* is supported but not the default configuration method (Arista EOS, Cisco IOS), the users can:

* Set the **netlab_config_mode** node parameter to `netmiko`
* Set the **defaults.devices._device_.group_vars.netlab_config_mode** (or the provider-specific **defaults.devices._device_._provider_.group_vars.netlab_config_mode**) [topology default](topo-defaults) to `netmiko`
* Use the **netlab install netmiko** command to install the *netmiko* library and set the **netlab_config_mode** in the [user defaults](defaults-user-file) of all devices that list `netmiko` in their **features.initial.config_mode** device feature.

```{tip}
The *libvirt* provider supports only the configuration methods specified in the **defaults.providers.libvirt.config_mode** list (`netmiko`, `sh`, and `cp_sh`).
```

## Device Settings

The *netmiko* configuration method uses the following device features (specified in the **features.netmiko** dictionary in the device settings):

{.table-wrap}
| Feature | Type | Meaning |
|---------|------|---------|
| **device_type** | string | *netmiko* device type (mandatory). See [netmiko documentation](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md) for the list of supported values |
| **error_regexp** | string or list | Regular expression(s) used to detect errors in the device responses to configuration commands. A list of regular expressions is combined into a single regular expression matching any of them |
| **delay** | int | Delay (in seconds) between establishing the SSH session and sending the first configuration snippet |
| **step_config** | bool | Exit the configuration mode after every configuration snippet |

These are the *netmiko* features used by the devices supporting the *netmiko* configuration method:

**Arista EOS** (`eos.yml`):

```
netmiko:
  device_type: arista_eos
  error_regexp: "^%.*"
```

**Cisco IOS** (`ios.yml`):

```
netmiko:
  device_type: cisco_ios
  error_regexp:
  - (?i:invalid|incomplete|ambiguous|error|overlap|enabled|bad).*
```

**Cisco Nexus OS** (`nxos.yml`):

```
netmiko:
  device_type: cisco_nxos
  error_regexp: [ "^%(?!INFO).*", "(?i:invalid|error).*" ]
```

**Cisco IOS XR** (`xr.yml`):

```
netmiko:
  device_type: cisco_xr
  delay: 2                    # Wait two seconds before trying to configure the device
  error_regexp: "^%.*"
  step_config: True
```

**IP Infusion OcNOS** (`ocnos.yml`):

```
netmiko:
  device_type: ipinfusion_ocnos
  error_regexp:                 # OcNOS errors start with '%'; '% Warning' lines are informational
  - "^%(?! Warning).*"
  step_config: true
```

```{tip}
The **error_regexp** regular expression should match the whole error message, not just its first few characters. The matched text is included in the error message _netlab_ displays when the configuration deployment fails.
```

The *netmiko* connection parameters are derived from these Ansible group variables (they could be set as device **group_vars** or as node parameters):

| Ansible variable | *netmiko* parameter | Mandatory |
|------------------|---------------------|:---------:|
| **ansible_user** | **username** | ✅ |
| **ansible_ssh_pass** | **password** | ✅ |
| **ansible_become_password** | **secret** (used by the **enable** command) | ❌ |

The SSH session is established with the node's management IPv4 address (**mgmt.ipv4**) or IPv6 address (**mgmt.ipv6**) when the node has no IPv4 management address. _netlab_ cannot use *netmiko* to configure nodes without a management IP address.

## Creating the Configuration Snippets

When the **netlab_config_mode** is set, the provider modules (*clab* and *libvirt*) add all configuration snippets used by the node (**normalize** when the device has the **features.initial.normalize** feature, **initial**, all modules specified in the node **module** list, and all custom configuration templates specified in the node **config** list) to the internal **_node_config** dictionary. The *netmiko* entries in that dictionary have the value `:netmiko` (they have no target file name).

The configuration snippets are also added to the **netlab_ansible_skip_module** list to prevent the Ansible playbook from deploying them a second time.

The **netlab initial** command renders the configuration templates into the `node_files/_nodename_` directory using the [regular configuration template search process](dev-config-deploy-paths) (the platform name used in template file names is the value of the **netlab_device_type** or **ansible_network_os** variable). The rendered files have no suffix; for example, the initial device configuration of node *r1* is in `node_files/r1/initial`.

You can use the same configuration templates for Ansible and *netmiko* configuration methods. The configuration templates contain configuration commands that are sent to the device in configuration mode, and you can use the device configuration mode commands (for example, **do** commands on Arista EOS) in them.

If you need a configuration method-specific configuration command, use the **netlab_config_mode** variable in the configuration template. For example, the Arista EOS **normalize** template disables interface PHY emulation when the configuration is deployed with *netmiko*:

```jinja
{% for intf in interfaces if intf.virtual_interface is not defined %}
!
interface {{ intf.ifname }}
{%   if netlab_config_mode in ['netmiko','sh'] %}
 platform tfa phy control-frame disabled
{%   endif %}
{% endfor %}
```

## Deploying the Configuration Snippets

The configuration deployment process is implemented in the **netsim.cli.initial.netmiko** module (using utility functions from **netsim.utils.netmiko** module) and is executed as part of the **netlab initial** command (which is also called as the last step of **netlab up**):

* **netlab initial** waits for the devices to become ready (see [](dev-config-deploy-paths)), and then starts a separate configuration deployment thread for every node.
* Nodes with the **netlab_config_mode** set to `netmiko` are configured with the *netmiko* library. All other configuration snippets (or nodes) are configured afterwards with the **netlab initial** Ansible playbook.
* If a device needs the *normalize* step, the **normalize** configuration snippet is deployed in a separate run before the **initial** configuration snippet is deployed.

_netlab_ uses this procedure to deploy configuration snippets with *netmiko*:

* Opens an SSH session to the device using **netmiko.ConnectHandler** and executes the **enable** command (using **ansible_become_password** as the *enable secret*)
* Waits for the **features.netmiko.delay** seconds (when specified)
* Executes the **send_config_from_file** function for every configuration snippet, using the **features.netmiko.error_regexp** regular expression to detect configuration errors.
* Executes the **commit** command when the *netmiko* device driver supports it (for example, on Cisco IOS XR)
* Exits the configuration mode when the **features.netmiko.step_config** device feature is set.
* Resets the base prompt after the **normalize** or **initial** configuration (the initial device configuration usually changes the device hostname)

The configuration deployment stops on the first configuration error, and the remaining configuration snippets are not deployed. _netlab_ displays the error message (including the text matched by the **error_regexp** expression) and the name of the session log file.

After the configuration deployment threads (and the Ansible playbook) complete, **netlab initial** displays the summary of *netmiko*-deployed configuration snippets.

### Deploying Custom Configuration Templates

The **netlab config** command uses the same deployment process for custom configuration templates when the node uses the *netmiko* configuration method. The **netlab config --reload** command always uses the Ansible playbook to reload the saved device configurations.

## Troubleshooting

* *netmiko* writes the log of all SSH session interactions to `node_files/_nodename_/netmiko.log`
* Use the **netlab initial --debug netmiko** command to display the *netmiko* connection parameters, the error-detection regular expression, and the device responses to the configuration commands
* Use the **netlab initial -o** command to create the configuration snippets in the `config` directory without deploying them
* Use the **netlab initial --dry-run** command to display the configuration snippets that would be deployed

## Tests

You can use any integration test (see [](dev-config-initial-tests)) to test the *netmiko* configuration method. To use the *netmiko* configuration method on a device that uses a different configuration method by default, set the **netlab_config_mode** device group variable with a CLI parameter; for example:

```
netlab up -d eos -s defaults.devices.eos.group_vars.netlab_config_mode=netmiko <test>
```

The `tests/config` directory contains topologies that can be used to test the error detection on Cisco IOS (`ios-netmiko.yml`), Nexus OS (`nxos-netmiko.yml`), and OcNOS (`ocnos-netmiko.yml`) with the **netlab config** command. For example, to verify that the *netmiko* configuration method detects invalid configuration commands on Cisco IOS:

* Start the lab with `netlab up ios-netmiko.yml`
* Execute `netlab config invalid` to deploy an invalid configuration command; the configuration deployment should fail.
