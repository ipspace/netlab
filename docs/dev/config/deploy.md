(dev-config-deploy)=
# Deploying Device Configurations

*netlab* Ansible playbooks deploy configurations through device-specific task lists and templates. When adding a new device type, you'll have to create either a generic _deploy configuration_ task list and a bunch of configuration templates or a task list for every module supported by the device (plus the initial configuration templates).

You can also mix and match the two approaches. For example, you could have a generic *deploy configuration* task list but use a separate list of tasks for the initial configuration.

(dev-config-deploy-paths)=
## Configuration Deployment Search Paths

Before starting the configuration deployment process, **netlab initial** Ansible playbook tries to find an Ansible task list that can be used to check the readiness of a lab device. If that task list is found, it's executed before the initial device configuration deployment starts. You can use that task list to check the device's SSH server (Arista cEOS) or interface initialization state (Cisco Nexus OS). **netlab initial** uses these default parameters to find the device readiness task list ([more details](deploy-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.ready.dirs** | Directory search path for device readiness task list |
| **paths.ready.files** | Filename search pattern for device readiness task list |

The **netlab initial** Ansible playbook tries to find device-specific task lists or templates using *netlab_device_type* or *ansible_network_os* (when *netlab_device_type* is missing) Ansible variable, including a combination with *netlab_provider* (for provider-specific configuration). These variables are usually defined as device group variables in system settings.

Directory- and file search paths are defined in these default parameters ([more details](deploy-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.templates.dir** | Directory search path for configuration templates |
| **paths.t_files.files** | Filename search patterns for configuration templates |

(deploy-task-list)=
After finding the Jinja2 template, the initial configuration deployment playbook tries to find the device/module-specific Ansible task list to deploy the configuration (*config_module* is set to *initial* when deploying the initial device configuration). The task list search process uses these default parameters ([more details](deploy-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.deploy.dirs** | Directory search paths for configuration deployment task lists |
| **paths.deploy.files** | Filename search patterns for module configuration deployment task lists |

(dev-find-custom)=
## Finding Custom Configuration Templates

The following paths are searched when looking for custom configuration templates specified in the **config** list or through a plugin ([more details](deploy-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.custom.dirs** | Directory search paths for custom configuration templates |
| **paths.custom.files** | Filename search patterns for custom configuration templates |

The custom configuration could be deployed via a dedicated task list or a generic configuration deployment task list. These parameters are used to find the custom configuration deployment task ([more details](deploy-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.custom.dirs** | Directory search paths for custom configuration deployment tasks |
| **paths.custom.tasks** | Filename search patterns for custom configuration deployment tasks |
| **paths.deploy.tasks_generic** | Generic configuration deployment task lists<br>(used to deploy custom configuration) |

If the deployment playbook cannot find a dedicated deployment tasklist, it uses the default tasklist that [depends on the device type and virtualization provider](deploy-task-list).

(deploy-ansible-variables)=
## Ansible Variables

The following Ansible variables are set before a device-specific task list is executed:

* `config_template` -- configuration template name (warning: the presence of configuration template might not be checked)
* `netsim_action` -- action currently being executed (`initial`,  module name, or custom configuration name)
* `config_module` -- the name of the currently-deployed module (present only in the module configuration deployment phase of **netlab initial**)
* `custom_config` -- the name of the currently-deployed custom configuration (present only in the custom configuration deployment phase of **netlab initial**)

## Sample Configuration Deployment Task Lists

Most network devices need a minimal configuration deployment task list, for example (Cisco IOS):

```
- cisco.ios.ios_config:
    src: "{{ config_template }}"
```

Some deployment task lists are a bit more complex. For example, Cumulus VX/FRR configuration deployment could use **bash** or **vtysh**:

```
- template:
    src: "{{ config_template }}"
    dest: /tmp/config.sh
- set_fact: deployed_config={{ lookup('template',config_template) }}
- command: bash /tmp/config.sh
  when: not ansible_check_mode and ("#!/bin/bash" in deployed_config)
- command: vtysh -f /tmp/config.sh
  when: not ansible_check_mode and not ("#!/bin/bash" in deployed_config)
```

Mikrotik RouterOS deployment copies a configuration file to the device with **scp** and executes an *import* command on the device:

```
- local_action:
    module: tempfile
    state: file
    suffix: temp
    prefix: ansible.{{ inventory_hostname }}.
  register: tempfile_1

- local_action:
    module: template
    src: "{{ config_template }}"
    dest: "{{ tempfile_1.path }}"

- local_action:
    module: command
    cmd: "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {{ lookup('env', 'HOME') }}/.vagrant.d/insecure_private_key {{ tempfile_1.path }} vagrant@{{ ansible_host }}:config.rsc"

- routeros_command:
    commands: /import config.rsc

- local_action:
    module: file
    path: "{{ tempfile_1.path }}"
    state: absent
  when: tempfile_1.path is defined
```

You'll find even more complex examples in `deploy-config/srlinux.yml` and `deploy-config/sros.yml`

## Mixing Task Lists and Configuration Templates

Nexus OS configurations usually use configuration templates. `deploy-config/nxos.yml` task list is as trivial as the Cisco IOS one:

```
- cisco.nxos.nxos_config:
    src: "{{ config_template }}"
```

Unfortunately, the Nexus 9300v linecards become active almost a minute after completing the device boot. We could check whether the Ethernet interfaces are present every time a configuration template is deployed on Nexus 9300v; a more streamlined approach uses a separate task list for initial device configuration in `nxos/initial.yml`[^RL]:

[^RL]: We could have also used the *device readiness* task list.

```
- name: Wait for Eth1/1 to appear
  cisco.nxos.nxos_command:
    commands:
    - show interface brief
    wait_for:
    - result[0] contains Eth1
    interval: 5
    retries: 20

- cisco.nxos.nxos_config:
    src: "{{ config_template }}"
```

(deploy-search-paths)=
## Changing and Troubleshooting Search Paths

The directory- and filename search paths used by **netlab initial** and **netlab config** commands are defined in the **paths** dictionary within the [system defaults](defaults). You can change these parameters but cannot append values to them.

The filename search patterns can use Jinja2 expressions that rely on [Ansible variables](deploy-ansible-variables) set during the configuration deployment process. Directory search patterns can use these prefixes:

| Prefix | Meaning |
|--------|---------|
| `package:` | **networklab** package (system file) |
| `topology:` | Directory containing the current lab topology |

The directory search patterns are evaluated during the [data transformation process](../transform.md), and the absolute paths are stored in the Ansible inventory (in the **all** group) and the `netlab.snapshot.yml` file. You can use the **netlab inspect defaults.paths** command to display the transformed values (**netlab inspect** command is available after starting the lab or executing the **netlab create** command).

For example, the default custom configuration template directory  search path (**defaults.paths.custom.dirs**) contains these entries:

```
custom:                         # Custom configuration templates
  dirs:                         # ... search directories
  - "topology:"
  - "."
  - "~/.netlab"
  - "package:extra"
```

The evaluated search path that is stored in `netlab.snapshot.yml` might contain these values (the topology directory is equal to the current directory, **netlab** is executed from local Git directory):

```
$ netlab inspect defaults.paths.custom.dirs
- /home/user/BGP/session/2-asoverride
- /home/user/.netlab
- /home/user/net101/tools/netsim/extra
```