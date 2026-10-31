(dev-config-netmiko)=
# Deploying Device Configurations with Netmiko

_netlab_ can use the [netmiko](https://github.com/ktbyers/netmiko) library instead of Ansible playbooks to deploy device configurations. The *netmiko* configuration method opens an SSH session to the device, enters the configuration mode, and sends the rendered configuration snippets to the device line-by-line. It's much faster than an Ansible playbook, as it does not have to start a separate Ansible process (and a separate SSH session) for every configuration snippet.

_netlab_ can also use *netmiko* to:

* Check whether the device SSH server is ready (see [](dev-ready-ssh) and [](dev-config-netmiko-ssh-ready))
* Collect device configurations with the **netlab collect** command (see [](dev-config-netmiko-collect))
* Reload saved device configurations with the **netlab config --reload** command (see [](dev-config-netmiko-reload))

This document describes how the *netmiko* configuration method works and which device settings you have to define to use it. The *netmiko* configuration method is currently available on these platforms:

```{features}
- title: netmiko<br>device type
  text: >-
    "`" + netmiko.device_type + "`"
- title: Default<br>configuration<br>method
  enabled: group_vars.get('netlab_config_mode','') == 'netmiko'
- title: netmiko<br>required
  enabled: "netmiko.required"
```

These devices can use Netmiko for additional functionality:

```{features}
- title: Collect<br>configuration
  enabled: "netmiko.collect"
- title: Reload<br>configuration
  enabled: "netmiko.reload.command"
```

The device settings are in the `netsim/devices/<device>.yml` files.

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

To make *netmiko* the default configuration method for a device, set the **group_vars.netlab_config_mode** device parameter (or the provider-specific **_provider_.group_vars.netlab_config_mode** parameter). For example, Cisco Nexus OS uses this definition in the `nxos.yml` device settings file:

```
group_vars:
  netlab_config_mode: netmiko
```

On devices where *netmiko* is supported but not the default configuration method (for example, Cisco ASAv virtual machines), the users can:

* Set the **netlab_config_mode** node parameter to `netmiko`
* Set the **defaults.devices._device_.group_vars.netlab_config_mode** (or the provider-specific **defaults.devices._device_._provider_.group_vars.netlab_config_mode**) [topology default](topo-defaults) to `netmiko`
* Use the **netlab install netmiko** command to install the *netmiko* library and set the **netlab_config_mode** in the [user defaults](defaults-user-file) of all devices that list `netmiko` in their **features.initial.config_mode** device feature.

```{tip}
The *libvirt* provider supports only the configuration methods specified in the **defaults.providers.libvirt.config_mode** list (`netmiko`, `sh`, and `cp_sh`).
```

(dev-config-netmiko-missing)=
### Missing *netmiko* Library

The *netmiko* library is not a _netlab_ dependency; the users have to install it with the **netlab install netmiko** or **netlab install ansible** command. The node transformation code (**check_netmiko_config_mode** function in the **netsim.augment.nodes** module) checks whether the *netmiko* library is installed, and if it's missing:

* Removes the device-level **netlab_config_mode** group variable from all devices (and providers) used in the lab when its value is `netmiko` (or `sh`/`cp_sh` with the *libvirt* provider, which uses *netmiko* to copy and execute the configuration scripts). The provider-specific group variable is checked first, followed by the generic one.
* Displays a warning saying that the affected devices will be configured with Ansible playbooks.
* Reports a fatal error (missing dependency) for devices that have the **features.netmiko.required** feature set. Use that feature when the device cannot be used without *netmiko* (for example, Extreme VOSS cannot execute commands specified in the `ssh` command line, so the [SSH readiness check](dev-ready-ssh) has to use *netmiko*).

The node- and group-level **netlab_config_mode** variables are not changed; the configuration deployment for those nodes will fail if the *netmiko* library is missing.

You can override the *netmiko* presence check with the **defaults.netmiko.installed** setting (or the `NETLAB_NETMIKO_INSTALLED` environment variable). The transformation and error tests set it to `True` to make their results independent of the installed Python packages.

## Device Settings

The *netmiko* configuration method uses the following device features (specified in the **features.netmiko** dictionary in the device settings):

{.table-wrap}
| Feature | Type | Meaning |
|---------|------|---------|
| **device_type** | string | *netmiko* device type (mandatory). See [netmiko documentation](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md) for the list of supported values |
| **error_regexp** | string or list | Regular expression(s) used to detect errors in the device responses to configuration commands. A list of regular expressions is combined into a single regular expression matching any of them |
| **delay** | int | Delay (in seconds) between establishing the SSH session and sending the first configuration snippet |
| **step_config** | bool | Exit the configuration mode after every configuration snippet |
| **collect** | dict | Commands used to collect device configuration(s) with the **netlab collect** command (see [](dev-config-netmiko-collect)) |
| **reload** | dict | Parameters used to reload saved device configurations with the **netlab config --reload** command (see [](dev-config-netmiko-reload)) |
| **ssh_ready.command** | string | Command used in the *netmiko*-based SSH readiness check (see [](dev-config-netmiko-ssh-ready)) |
| **required** | bool | The device cannot be used without the *netmiko* library (see [](dev-config-netmiko-missing)) |

The *netmiko* connection parameters are derived from these Ansible group variables (they could be set as device **group_vars** or as node parameters):

| Ansible variable | *netmiko* parameter | Mandatory |
|------------------|---------------------|:---------:|
| **ansible_user** | **username** | ✅ |
| **ansible_ssh_pass** | **password** | ✅ |
| **ansible_become_password** | **secret** (used by the **enable** command) | ❌ |

The SSH session is established with the node's management IPv4 address (**mgmt.ipv4**) or IPv6 address (**mgmt.ipv6**) when the node has no IPv4 management address. _netlab_ cannot use *netmiko* to configure nodes without a management IP address.

### Examples

Arista EOS uses a simple error-detecting regular expression (anything starting with a percentage sign) and has to clean up LLDP configuration on interfaces:

**Arista EOS** (`eos.yml`):

```
netmiko:
  device_type: arista_eos
  error_regexp: "^%.*"
  collect:
    config: show running
    _config_clean: ^\s+no lldp (transmit|receive)$
  reload:
    config: replace-config
    command: 'configure replace flash:replace-config'
```

The error-detecting regular expression for Cisco IOS is significantly more complex (we have to catch the keywords that could indicate an error), but the cleanup of the collected configuration is easier -- the first few lines have to be removed. The configuration reload has to enable the SCP server and uses the *netmiko* **file_transfer** function to copy the saved configuration into NVRAM.

**Cisco IOS** (`ios.yml`):

```
netmiko:
  device_type: cisco_ios
  collect:
    config: show running-config
    _config_skip: 3
  error_regexp:
  - (?i:invalid|incomplete|ambiguous|error|overlap|enabled|bad).*
  reload:
    config: nvram:replace-config
    command: configure replace nvram:replace-config force
    configure: |
      ip scp server enable
    file_transfer: true
```

```{tip}
The **error_regexp** regular expression should match the whole error message, not just its first few characters. The matched text is included in the error message _netlab_ displays when the configuration deployment fails.
```

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

The **netlab config** command (implemented in the **netsim.cli.config** package) uses the same deployment process for custom configuration templates when the node uses the *netmiko* configuration method.

(dev-config-netmiko-reload)=
## Reloading Saved Device Configurations

The **netlab config --reload** command (also used by **netlab up --reload-config**) can use *netmiko* to copy the saved device configuration to the device and replace the running configuration with it. The implementation is in the **netsim.cli.config.reload** module:

* *netmiko* is used for nodes whose device settings include the **features.netmiko.reload.command** feature, provided the *netmiko* library is installed and _netlab_ can prepare the *netmiko* connection parameters. The *netmiko*-based reload does not depend on the **netlab_config_mode** setting.
* The configuration reload is executed in a separate thread for every node.
* The remaining nodes are processed with the **reload-config.ansible** Ansible playbook.

The *netmiko* configuration reload uses these features (specified in the **features.netmiko.reload** dictionary):

{.table-wrap}
| Feature | Type | Meaning |
|---------|------|---------|
| **command** | string | The *replace configuration* command executed after the saved configuration has been copied to the device (mandatory) |
| **config** | string | Destination file name (default: `replace-config`). It can include a file system prefix (for example, `nvram:replace-config`) |
| **configure** | string or list | Configuration commands to execute before copying the file (for example, to enable the SCP server) |
| **file_transfer** | bool | Use the *netmiko* **file_transfer** function instead of the generic SCP client to copy the configuration file (default: `False`). The file system prefix in the **config** value is passed to the **file_transfer** function as the **file_system** parameter |
| **success** | string | Regular expression matching a successful *replace configuration* printout |

_netlab_ uses this procedure to reload a saved configuration with *netmiko*:

* Opens an SSH session to the device and executes the **enable** command
* Executes the **reload.configure** configuration commands (when specified)
* Copies the saved configuration (`<node>.<suffix>` file in the configuration directory) to the device using the generic SCP client (based on the SSH session established by *netmiko*) or the *netmiko* **file_transfer** function.
* Executes the **reload.command** command and checks its printout. The reload is successful when the printout matches the **reload.success** regular expression (when specified) or when it does not match the **features.netmiko.error_regexp** regular expression.

**netlab config --reload** exits with an error status if the configuration reload failed on any device.

(dev-config-netmiko-ssh-ready)=
## SSH Readiness Check

The SSH server [readiness check](dev-ready-ssh) uses *netmiko* when the *netmiko* library is installed, the device has the **features.netmiko.device_type** feature, and _netlab_ can prepare the *netmiko* connection parameters.

The *netmiko*-based SSH check executes the **features.netmiko.ssh_ready.command** command (when specified) or the **netlab_check_command** command (default: `show version`). Use the **ssh_ready.command** feature when the command executed with *netmiko* has to differ from the one executed with the `ssh` command (for example, ASAv uses `exit` with `ssh` and `show version` with *netmiko*). When the **ssh_ready.command** is an empty string, the *netmiko* probe checks only whether it can log into the device.

If the *netmiko* library is missing and the device has the **features.netmiko.required** feature, the SSH readiness check reports an error.

(dev-config-netmiko-collect)=
## Collecting Device Configurations

The **netlab collect** command tries to collect device configurations with internal collection methods (currently only *netmiko*) before falling back to the **collect-configs.ansible** Ansible playbook. The internal collection is implemented in the **netsim.cli.collect** module (the *netmiko*-specific code is in the **netsim.cli.collect.netmiko** module) and works like this:

* **netlab collect** starts a separate collection thread for every collectable node and tries all internal collection methods (listed in the **INTERNAL_DISPATCH** dictionary) for that node.
* A collection method returns `None` when it cannot be used with the node, `True` when it collected the device configuration, and `False` when the collection failed.
* Nodes for which an internal collection method returned `True` or `False` are added to the Ansible skip list and are not processed by the **collect-configs.ansible** playbook.
* The Ansible playbook is executed only when there are nodes left whose configurations have not been collected with an internal method. If some configurations were already collected with an internal method, **netlab collect** displays an extra section header before starting the Ansible playbook.

The *netmiko* collection method is used for devices that have the **features.netmiko.collect** dictionary. It does not depend on the **netlab_config_mode** setting; _netlab_ uses *netmiko* to collect the configuration of a supported device even when the device was configured with Ansible playbooks.

The keys of the **features.netmiko.collect** dictionary are configuration names, and the values are the commands used to display the configuration. The keys starting with an underscore are cleanup parameters for the configuration with the same name (`<name>` is the configuration name):

{.table-wrap}
| Key | Type | Meaning |
|-----|------|---------|
| `<name>` | string | Command used to collect the *name* configuration |
| `_<name>_skip` | int | Number of lines to skip at the beginning of the command printout (for example, the *Building configuration* and *Current configuration* lines on Cisco IOS) |
| `_<name>_clean` | string | Regular expression used to remove lines from the command printout. All lines matching the regular expression are removed |

The configuration collected with the **config** command is saved into the `<node>.<suffix>` file in the output directory (the default suffix is `cfg`). All other configurations are saved into the `<node>-<name>` files. 

_netlab_ uses this procedure to collect the device configurations with *netmiko*:

* Prepares the *netmiko* connection parameters and opens an SSH session to the device using the same functions (and the same Ansible group variables) as the *netmiko* configuration method.
* Executes the **send_command** function for every configuration name, skips the configurations that returned empty printouts, cleans up the printout using the `_<name>_skip` and `_<name>_clean` parameters, and saves the results into the output directory.

The collection method returns `None` (allowing _netlab_ to use the Ansible playbook for that node) when it cannot prepare the *netmiko* connection parameters or when **send_command** returns a value that is not a string. It returns `False` (and reports an error) when it cannot connect to the device or when an exception is raised during the collection.

To add *netmiko*-based configuration collection to a device that already supports the *netmiko* configuration method:

* Add the **features.netmiko.collect** dictionary to the device settings
* Run the `tests/integration/initial/x-91-collect.yml` integration test, and compare the collected configuration (in the `config` directory) with the configuration collected with the Ansible playbook. Add the `_config_skip` and `_config_clean` parameters to remove the unwanted lines.
* Make sure the collected configuration can be used with the **netlab up --reload-config** command.

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

The `tests/config` directory contains topologies that can be used to test the error detection on Cisco ASAv (`asa-netmiko.yml`), Cisco IOS (`ios-netmiko.yml`), Nexus OS (`nxos-netmiko.yml`), and OcNOS (`ocnos-netmiko.yml`) with the **netlab config** command. For example, to verify that the *netmiko* configuration method detects invalid configuration commands on Cisco IOS:

* Start the lab with `netlab up ios-netmiko.yml`
* Execute `netlab config invalid` to deploy an invalid configuration command; the configuration deployment should fail.

The `tests/integration/initial/x-91-collect.yml` integration test executes the **netlab collect** command instead of the validation step. Use it to test the *netmiko*-based configuration collection.

The `tests/integration/initial/10-reload.yml` integration test saves the device configurations, restarts the lab, and reloads the saved configurations. Use it to test the *netmiko*-based configuration reload.
