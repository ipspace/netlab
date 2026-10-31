(dev-ready)=
# Device Readiness Checks

Virtualization providers often report that a lab device has started long before it can be configured. For example, *containerlab* declares success as soon as the containers are running, even when they contain virtual machines that need minutes to boot, and some devices accept SSH sessions before they detect their data-plane interfaces.

**netlab initial** (and **netlab config --reload**) thus starts with a sequence of *device readiness checks*. This document describes how those checks are selected, executed, and configured, and how you can add readiness checks for a new device.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## When Are the Readiness Checks Executed?

The readiness checks are executed:

* As the first step of the configuration deployment process in **netlab initial** (and thus **netlab up**) unless the (internal) `--skip-ready` flag is set.
* Before reloading saved device configurations with **netlab config --reload**.
* As the only action of the **netlab initial --ready** command. You can use that command in [CLI hooks](dev-cli-hooks) or when testing the readiness checks of a new device.

The readiness checks are executed only on nodes that will be configured (the nodes specified with the `--limit` parameter, excluding [unprovisioned](group-special-names) nodes).

The readiness checks are implemented in the `netsim/cli/initial/ready` package.

(dev-ready-steps)=
## Selecting the Readiness Checks

The readiness checks executed on a node are specified in the **netlab_ready** group variable, a list of *readiness steps*. As with other group variables, you can set it for a device (**group_vars.netlab_ready**), for a device/provider combination (**_provider_.group_vars.netlab_ready**), or on an individual node.

These readiness steps are recognized by *netlab*:

{.table-wrap}
| Step | Description | Handler |
|------|-------------|---------|
| **health** | [Wait for the virtualization provider to report healthy nodes](dev-ready-health) | internal (Python) |
| **ssh** | [Wait for a working SSH server](dev-ready-ssh) | internal or Ansible playbook |
| **command** | [Wait for a CLI command to return the expected result](dev-ready-command) | internal (Python) |
| **ansible** | [Execute a device-specific Ansible task list](dev-ready-ansible) | Ansible playbook |

Notes:

* *netlab* performs no readiness checks on devices that do not have the **netlab_ready** variable. That's perfectly fine for devices started with Vagrant (Vagrant waits for the SSH server) or for Linux containers that are configured with `docker exec`.
* The order of the steps in the **netlab_ready** list is irrelevant. The readiness checks are always executed in this order: **health**, **ssh**, **command**, and finally the Ansible playbook (that includes the **ansible** step).
* Every step is executed in parallel on all nodes that need it. The next step starts after all the nodes have completed the previous step.
* A failed readiness check aborts the lab configuration process.
* Some devices set **netlab_ready** to `[ ansible ]` without having an Ansible readiness task list. That's a trick to skip the SSH readiness check that would otherwise be inherited from another device or a provider-specific setting.

**Example:** Cisco Nexus OS uses the [command readiness check](dev-ready-command) on all virtualization providers. It also has to wait for the SSH server when running in a *vrnetlab* container:

```
group_vars:
  netlab_ready: [ command ]
  netlab_check_retries: 50
  netlab_check_delay: 10
clab:
  group_vars:
    netlab_ready: [ ssh, command ]
  features:
    initial:
      healthcheck: true
```

(dev-ready-internal)=
### Internal and Ansible Handlers

The **defaults.netlab.initial.ready** dictionary specifies which readiness steps are executed with internal (Python) code:

```
netlab:
  initial:
    ready:
      ssh: internal
      health: internal
      command: internal
```

The readiness steps that are not handled internally (including the **ansible** step) are executed with the `device-ready.ansible` playbook, with Ansible tags set to `ready_`_step_ for every step that has to be executed.

The `device-ready.ansible` playbook implements only the **ssh** and **ansible** steps. Changing the **health** or **command** handler to anything but `internal` thus disables those checks.

The playbook selects the target hosts with the `netlab_ready_`_step_ Ansible inventory groups. The **ansible** output module (`netsim/outputs/ansible.py`) creates those groups from the **netlab_ready** values of individual nodes.

(dev-ready-timing)=
### Wait Times

All readiness checks use these group variables (that can also be set on individual nodes) to control the wait time:

{.table-wrap}
| Variable | Default | Meaning |
|----------|--------:|---------|
| **netlab_check_retries** | 20 | Number of retries |
| **netlab_check_delay** | 5 | Delay between retries/timeout of a single attempt (seconds) |

The internal handlers compute the maximum wait time as **netlab_check_retries** × **netlab_check_delay** (100 seconds with the default values) and keep retrying the check until it succeeds or the wait time expires. The Ansible task lists should use the same variables in their `retries` and `delay` parameters.

(dev-ready-health)=
## Provider Health Check

The **health** step calls the **health_check** method of all virtualization providers used by the nodes in the waitlist. The method receives the list of nodes that need the health check and the lab topology. The default implementation (in `netsim/providers/__init__.py`) does nothing.

Only the *containerlab* provider implements the health check:

* The provider **init** hook (`health_ready_setup` in `netsim/providers/clab/labops.py`) adds the **health** step to the **clab.group_vars.netlab_ready** list of every device with the **clab.features.initial.healthcheck** feature (copying the device **group_vars.netlab_ready** value into the provider-specific group variables first).
* The **health_check** method executes **containerlab inspect** every second until all specified containers report the *healthy* state or until the **defaults.providers.clab.healthy_timeout** (default: 600 seconds) expires.
* The health check is disabled when **defaults.providers.clab.healthy_timeout** is set to zero.

To use the health check on a new *containerlab* device (usually a *vrnetlab* container), set the **clab.features.initial.healthcheck** device feature to *True*:

```
clab:
  features:
    initial:
      healthcheck: true
```

```{tip}
A *healthy* *vrnetlab* container does not imply a working SSH server. You'll probably have to add the **ssh** step to the **clab.group_vars.netlab_ready** list.
```

(dev-ready-ssh)=
## SSH Server Check

The **ssh** step waits until *netlab* can log into the device using SSH and execute a CLI command. The internal implementation is in `netsim/cli/initial/ready/ssh.py`:

* *netlab* uses *netmiko* to connect to the device and execute the command when the *netmiko* library is installed and the device has the **netmiko.device_type** feature (see [](dev-config-netmiko-ssh-ready) for details). All *netmiko* timeouts are set to **netlab_check_delay**. The command executed with *netmiko* can be changed with the **netmiko.ssh_ready.command** device feature.
* Devices that cannot be checked with the `ssh` command (for example, Extreme VOSS) set the **netmiko.required** device feature; the SSH check reports an error on those devices when the *netmiko* library is missing.
* Otherwise, *netlab* executes the `ssh` command (prefixed with `sshpass` when the **ansible_ssh_pass** variable is set) with a **netlab_check_delay** timeout.
* Both methods connect to the node management IPv4 address (or IPv6 address if the node has no IPv4 management address) using the **ansible_user** username. The SSH check fails if the node has no management IP address.
* The check is retried (once per second) until it succeeds or the [maximum wait time](dev-ready-timing) expires.
* The maximum wait time is increased to **defaults.providers._provider_.ssh_timeout** if that value is set and larger than the computed wait time.

These group variables control the SSH server check:

{.table-wrap}
| Variable | Meaning |
|----------|---------|
| **ansible_user** | SSH username |
| **ansible_ssh_pass** | SSH password (requires `sshpass` when *netmiko* cannot be used) |
| **netlab_check_command** | CLI command to execute (default: `show version`). Use a different command if your device does not support it (example: `who` on cRPD) |
| **netlab_ssh_args** | Extra arguments for the `ssh` command (for example, legacy key exchange algorithms) |

The Ansible implementation of the SSH check (`netsim/ansible/tasks/readiness-check/ssh.yml`) is used when **defaults.netlab.initial.ready.ssh** is set to **ansible**. It executes the same `ssh` command with a 10-second timeout, retrying it **netlab_check_retries** times with a **netlab_check_delay** delay.

(dev-ready-command)=
## Command Check

The **command** step waits until a CLI command executed on the device returns the expected output (for example, until the device detects its first data-plane interface). The internal implementation is in `netsim/cli/initial/ready/command.py`; it uses the **[netlab connect](netlab-connect)** code to execute the command, so it works with SSH and **docker exec** connections (selected with the **netlab_console_connection** or **ansible_connection** group variable).

The command check is configured with the **command.ready** device feature, a dictionary with these keys:

{.table-wrap}
| Key | Meaning |
|-----|---------|
| **execute** | The command to execute on the device |
| **expect** | A string that must appear in the command output |
| **when** | Optional Python expression. The command check is skipped when the expression evaluates to *False* |

The **when** expression and the **execute** and **expect** strings (evaluated as Python f-strings) can use all node attributes and the **phy_interfaces** variable, the list of node interfaces without the **virtual_interface** attribute.

**Example:** Cisco Nexus OS command readiness check (`netsim/devices/nxos.yml`) waits for the first physical interface to appear in the **show interface brief** printout:

```
features:
  command:
    ready:
      when: phy_interfaces
      execute: show interface brief
      expect: '{phy_interfaces[0].ifname.replace("Ethernet","Eth")}'
```

The command is executed every **netlab_check_delay** seconds (at least once per second) until its output contains the **expect** string or until the [maximum wait time](dev-ready-timing) expires. If the command execution fails (for example, the SSH session cannot be established), the check is retried, but only for a quarter of the maximum wait time; in that case *netlab* reports the last error it encountered.

```{warning}
A device with the **command** step in its **netlab_ready** list must have the **command.ready** feature; *netlab* reports an internal error otherwise.
```

(dev-ready-ansible)=
## Ansible Readiness Task List

The **ansible** step executes a device-specific Ansible task list. Use it when the device needs a readiness check that cannot be implemented with the generic mechanisms described above, for example:

* Waiting for a Linux service (`cumulus_nvue.yml`)
* Waiting for a HTTPS (`fortios-clab.yml`) or gNMI (`sros.yml`) server
* Executing a device-specific command over a NETCONF or REST API connection (`junos.yml`, `netscaler.yml`)

The `device-ready.ansible` playbook executes the `tasks/wait-for-ready.yml` task list on all hosts in the `netlab_ready_ansible` inventory group. That task list finds the device readiness task list using the **paths.ready.dirs** directory search path and the **paths.ready.files** filename patterns ([more details](change-search-paths)):

```
ready:
  dirs:
  - "topology:readiness-check"
  - "readiness-check"
  - "~/.netlab/readiness-check"
  - "/etc/netlab/readiness-check"
  - "package:ansible/tasks/readiness-check"
  files:
  - "{{netlab_device_type}}-{{node_provider}}.yml"
  - "{{netlab_device_type}}.yml"
  - "{{ansible_network_os}}-{{node_provider}}.yml"
  - "{{ansible_network_os}}.yml"
```

The system readiness task lists are thus stored in the `netsim/ansible/tasks/readiness-check` directory, and the task list name is based on the **netlab_device_type** variable (or **ansible_network_os** when **netlab_device_type** is not set), optionally combined with the node provider (example: `vyos-clab.yml`). The task list is skipped if no matching file is found.

```{warning}
The Ansible readiness task list is executed only on nodes that have the **ansible** step in their **netlab_ready** list.
```

The readiness task list is executed with **gather_facts** set to *false*. The playbook sets the **netlab_device_type**, **netlab_interfaces**, and **node_provider** variables before executing the task list. Use **netlab_check_retries** and **netlab_check_delay** variables (with device-specific defaults) to control the wait time, for example:

```
- name: Check {{ inventory_hostname }} nscli readiness
  ansible.builtin.raw: nscli -U '127.0.0.1:{{ ansible_user }}:{{ ansible_ssh_pass }}' 'show ns hostName'
  changed_when: False
  register: command_out
  until: command_out.rc == 0 and "Done" in command_out.stdout
  retries: "{{ netlab_check_retries | default(60) }}"
  delay: "{{ netlab_check_delay | default(5) }}"
```

(dev-ready-new-device)=
## Adding Readiness Checks to a New Device

Use these guidelines to select the readiness checks for a new device:

* Devices started by Vagrant usually don't need the **ssh** step (Vagrant waits for the SSH server).
* *vrnetlab* containers usually need the **health** check (set **clab.features.initial.healthcheck**) and the **ssh** step (in **clab.group_vars.netlab_ready**).
* Use the **command** step for devices that accept SSH sessions before they're ready to be configured (for example, before they detect data-plane interfaces). Prefer it over an Ansible task list; it's faster and does not depend on Ansible collections.
* Use the **ansible** step only when you cannot implement the readiness check with the internal handlers.
* Set **netlab_check_retries** and **netlab_check_delay** if the device needs more than 100 seconds to become ready.

## Troubleshooting

* Use **netlab initial --ready** to execute just the readiness checks.
* Use `--debug ssh` to display the SSH commands, wait times, and SSH errors (every five seconds).
* Use `--debug ready` to display the command check wait times, the command outputs, and the expected results.
* Use `-v` to display the readiness check progress even when the devices become ready in less than five seconds.
