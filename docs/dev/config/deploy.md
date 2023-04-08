# Deploying Device Configurations

*netlab* Ansible playbooks deploy configurations through device-specific task lists and templates. When adding a new device type, you'll have to create either a generic _deploy configuration_ task list and a bunch of configuration templates, or a task list for every module supported by the device (plus the initial configuration).

You can also mix-and-match the two approaches. For example, you could have a generic *deploy configuration* task list, but use a separate list of tasks for initial configuration.

## Search Paths

The Ansible playbooks try to find device-specific task lists or templates using *netlab_device_type* or *ansible_network_os* (when *netlab_device_type* is missing) Ansible variable, including a combination with *netlab_provider* (for provider-specific configuration). These variables are usually defined as device group variables in system settings.

Ansible playbooks use the following search path to find configuration templates within `netsim/ansible/templates` directory (*config_module* is set to *initial* for initial device configuration):

```
- "{{ config_module }}/{{netlab_device_type}}-{{ netlab_provider }}.j2"
- "{{ config_module }}/{{netlab_device_type}}.j2"
- "{{ config_module }}/{{ansible_network_os}}-{{ netlab_provider }}.j2"
- "{{ config_module }}/{{ansible_network_os}}.j2"
```

Initial configuration deployment playbook uses this search path to find device/module specific Ansible task list within `netsim/ansible/tasks` directory (*config_module* is set to *initial* for initial device configuration):

```
- "{{netlab_device_type}}/{{ config_module }}-{{ netlab_provider }}.yml"
- "{{netlab_device_type}}/{{ config_module }}.yml"
- "deploy-config/{{netlab_device_type}}-{{ netlab_provider }}.yml"
- "deploy-config/{{netlab_device_type}}.yml"
- "{{ansible_network_os}}/{{ config_module }}-{{ netlab_provider }}.yml"
- "{{ansible_network_os}}/{{ config_module }}.yml"
- "deploy-config/{{ansible_network_os}}-{{ netlab_provider }}.yml"
- "deploy-config/{{ansible_network_os}}.yml"
```

## Finding Custom Configuration Templates

The following paths are searched when looking for custom configuration templates specified in **config** list or through a plugin:

* Current directory (user plugins)
* `netsim/extra` directory (system plugins)

When looking for a custom configuration template in the above search path, the following names are tried (*custom_config* is the name of custom configuration template or directory):

```
- "{{ config + '/' + inventory_hostname + '.' + netlab_device_type + '-' + netlab_provider + '.j2' }}"
- "{{ config + '/' + inventory_hostname + '.' + netlab_device_type + '.j2' }}"
- "{{ config + '/' + inventory_hostname + '.j2' }}"
- "{{ config + '/' + netlab_device_type + '-' + netlab_provider + '.j2' }}"
- "{{ config + '/' + netlab_device_type + '.j2' }}"
- "{{ config + '/' + ansible_network_os + '-' + netlab_provider + '.j2' }}"
- "{{ config + '/' + ansible_network_os + '.j2' }}"
- "{{ config + '.' + inventory_hostname + '.' + netlab_device_type + '.j2' }}"
- "{{ config + '.' + inventory_hostname + '.' + ansible_network_os + '.j2' }}"
- "{{ config + '.' + inventory_hostname + '.j2' }}"
- "{{ config + '.' + netlab_device_type + '.j2' }}"
- "{{ config + '.' + ansible_network_os + '.j2' }}"
- "{{ config }}"
- "{{ config + '.j2' }}"
```

The custom configuration could be deployed via a dedicated task list or via generic configuration deployment task list (see above). The deployment process uses this search path:

```
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy-{{ inventory_hostname }}.yml"
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy.{{ netlab_device_type }}-{{ netlab_provider }}.yml"
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy.{{ netlab_device_type }}.yml"
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy.{{ ansible_network_os }}-{{ netlab_provider }}.yml"
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy.{{ ansible_network_os }}.yml"
- "{{ lookup('env','PWD') }}/{{ custom_config }}/deploy.yml"
- "../../extra/{{ custom_config }}/deploy.{{ netlab_device_type }}-{{ netlab_provider }}.yml"
- "../../extra/{{ custom_config }}/deploy.{{ netlab_device_type }}.yml"
- "deploy-config/{{netlab_device_type}}-{{ netlab_provider }}.yml"
- "deploy-config/{{netlab_device_type}}.yml"
- "../../extra/{{ custom_config }}/deploy.{{ ansible_network_os }}-{{ netlab_provider }}.yml"
- "../../extra/{{ custom_config }}/deploy.{{ ansible_network_os }}.yml"
- "deploy-config/{{ansible_network_os}}-{{ netlab_provider }}.yml"
- "deploy-config/{{ansible_network_os}}.yml"
- "../missing.yml"
```

## Ansible Variables

The following Ansible variables are set before a device-specific task list is executed:

* `config_template` -- configuration template name (warning: the presence of configuration template might not be checked)
* `netsim_action` -- action currently being executed (`initial`,  module name, or custom configuration name)
* `config_module` -- name of currently-deployed module (present only in the module configuration deployment phase of **netlab initial**)
* `custom_config` -- name of currently-deployed custom configuration (present only in the custom configuration deployment phase of **netlab initial**)

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

Nexus OS configurations usually use configuration templates. `deploy-config/nxos.yml` task list is as trivial as Cisco IOS one:

```
- cisco.nxos.nxos_config:
    src: "{{ config_template }}"
```

Unfortunately, the Nexus 9300v linecards become active almost a minute after the device boot is completed. We could check whether the Ethernet interfaces are present every time a configuration template is deployed on Nexus 9300v; a more streamlined approach uses a separate task list for initial device configuration in `nxos/initial.yml`:

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
