(dev-config-deploy)=
# Deploying Device Configurations

*netlab* Ansible playbooks deploy configurations through device-specific task lists and templates. Linux-based containers (including daemons such as Bird or dnsmasq, and routers such as FRRouting or VyOS) can also be configured using shell scripts.

When adding a new device type, you'll have to create either:

* A generic _deploy configuration_ task list and a bunch of configuration templates
* A module-specific task list for an individual module, plus the associated initial configuration templates (which could be empty)
* Linux scripts that can be mapped into container files and executed within the container network namespace on the _netlab_ host or within the container itself
* Daemon configuration files for container-based daemons (for example, Bird).

You can also mix and match the approaches. For example, several devices have a generic *deploy configuration* task list, but use a separate list of tasks for the initial configuration.

You could also use Linux scripts for some configuration modules, Daemon configuration files for other tasks, and an Ansible task list + template for the rest of the tasks (or custom templates). For example, Bird daemon uses configuration files to configure BGP and OSPF, shell scripts (inherited from the Linux device) to configure interfaces, VLANs, and link aggregation groups, and an Ansible task list (also inherited from the Linux device) to deploy custom configuration templates.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-config-create)=
## Creating Configuration Files and Scripts

**netlab create** (the *configs* output module) and **netlab initial** create device configuration files in the **node_files** directory. That directory contains a separate per-node subdirectory with node-specific configuration files.

The files in the per-node subdirectory are created from:

* [Daemon configuration files](dev-config-daemon)
* **normalize**[^WN] and **initial** configuration templates
* Module configuration templates for modules specified in the **module** node attribute
* Custom configuration templates for templates specified in the **config** node attribute.

```{tip}
The [](dev-config-deploy-paths) and [](dev-find-custom) sections describe how _netlab_ finds configuration templates
```

The node-specific configuration files (apart from daemon configuration files) are not created for nodes in the **unprovisioned** group. Daemon configuration files are always created.

The [*clab* provider](lab-clab) maps some files in the **node_files/_nodename_** directory to container files. The mappings are specified in the [**clab.binds** node attribute](lab-clab-binds) which is derived from [daemon configuration files](dev-config-daemon), [Linux configuration scripts](dev-config-script) and user-specified binds.

[^WN]: When the **features.initial.normalize** flag is set

(dev-config-deploy-paths)=
## Configuration Deployment Search Paths

Before starting the configuration deployment process, the **netlab initial** Ansible playbook tries to find an Ansible task list that can be used to check the readiness of a lab device. If that task list is found, it's executed before the initial device configuration deployment starts. You can use that task list to check the device's SSH server (Arista cEOS) or interface initialization state (Cisco Nexus OS). **netlab initial** uses these default parameters to find the device readiness task list ([more details](change-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.ready.dirs** | Directory search path for device readiness task list |
| **paths.ready.files** | Filename search pattern for device readiness task list |

The **netlab initial** Ansible playbook tries to find device-specific task lists or templates using *netlab_device_type* or *ansible_network_os* (when *netlab_device_type* is missing) Ansible variable, including a combination with *netlab_provider* (for provider-specific configuration). These variables are usually defined as device group variables in system settings.

Directory- and file search paths are defined in these default parameters ([more details](change-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.templates.dir** | Directory search path for configuration templates |
| **paths.t_files.files** | Filename search patterns for configuration templates |

```{warning}
_netlab_ assumes you're always using Jinja2-based device configuration templates. Add empty template files to the module-specific `netsim/ansible/templates` directory if you configure your device solely through an Ansible task list.
```

(deploy-task-list)=
After locating the Jinja2 template, the initial configuration deployment playbook attempts to retrieve the device/module-specific Ansible task list to deploy the configuration (*config_module* is set to *initial* when deploying the initial device configuration). The task list search process uses these default parameters ([more details](change-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.deploy.dirs** | Directory search paths for configuration deployment task lists |
| **paths.deploy.files** | Filename search patterns for module configuration deployment task lists |

```{tip}
Use the **‌netlab create --debug paths** command to display the components of individual search paths and the directories _netlab_ uses when searching those paths (non-existent directories are removed from the search paths)
```

(dev-find-custom)=
## Finding Custom Configuration Templates

The following paths are searched when looking for custom configuration templates specified in the **config** list or through a plugin ([more details](change-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.custom.dirs** | Directory search paths for custom configuration templates |
| **paths.custom.files** | Filename search patterns for custom configuration templates |

The custom configuration could be deployed via a dedicated task list or a generic configuration deployment task list. These parameters are used to find the custom configuration deployment task ([more details](change-search-paths)):

| Parameter | Usage |
|-----------|-------|
| **paths.custom.dirs** | Directory search paths for custom configuration deployment tasks |
| **paths.custom.tasks** | Filename search patterns for custom configuration deployment tasks |
| **paths.deploy.tasks_generic** | Generic configuration deployment task lists<br>(used to deploy custom configuration) |

If the deployment playbook cannot find a dedicated deployment tasklist, it uses the default tasklist that [depends on the device type and virtualization provider](deploy-task-list).

```{warning}
You must have a deployment task list **‌and** a dummy configuration template in the custom configuration directory to use an Ansible task list to deploy a custom configuration change.

For example, the custom configuration directory MUST contain `deploy.fortinet.fortios.fortios.yml` and (potentially empty) `fortinet.fortios.fortios.j2` files to deploy custom configuration on Fortinet devices.
```

(deploy-ansible-variables)=
## Ansible Variables

The following Ansible variables are set before a device-specific task list is executed:

* `config_template` -- configuration template name
* `netsim_action` -- action currently being executed (`initial`,  module name, or custom configuration name)
* `config_module` -- the name of the currently-deployed module (present only in the module configuration deployment phase of **netlab initial**)
* `custom_config` -- the name of the currently-deployed custom configuration (present only in the custom configuration deployment phase of **netlab initial**)

## Sample Configuration Deployment Task Lists

Most network devices need a minimal configuration deployment task list, for example, Cisco IOS:

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

You'll find even more complex examples in `deploy-config/srlinux.yml` and `deploy-config/sros.yml`.

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

(dev-config-daemon)=
## Daemon Configuration Files

You can use Jinja2 templates to create *daemon configuration files* mapped into daemon containers. These files are present in the container file system when the container starts and can be used to configure the daemon (e.g., Bird or dnsmasq) running in the container.

The daemon configuration files are specified in the **daemon_config** device parameter. These are the configuration files used by the Bird daemon:

```
daemon_config:
  bird: /etc/bird/bird.conf
  bgp: /etc/bird/bgp.mod.conf
  ospf: /etc/bird/ospf.mod.conf
  routing: /etc/bird/routing.mod.conf
```

The keys of the **daemon_config** dictionary can (but don't have to) match _netlab_ module names. If a daemon configuration key matches a module name, _netlab_ does not try to configure that module in the Ansible playbook.

The daemon configuration templates are usually stored in the `netsim/daemons/_daemon_` directory, but could be anywhere in the template search path. These templates can also include other templates in the template search path.

The **daemon_config** templates are copied into the **clab.config_templates** node parameter, which is then used to create **clab.binds** mapping between files within the `clab_files` directory structure and container files. The templates are rendered (within the `clab_files` structure) during the **netlab create**/**netlab up** process and are thus available to processes running inside the containers when the containers start.

(dev-config-script)=
## Linux Configuration Scripts

Some Linux-based containers (Linux nodes, Linux-based Daemons, FRRouting, and VyOS) can be configured with Linux scripts. These scripts can be executed within a container or within the container network namespace on the host (for containers that do not have the *iproute* package installed).

The scripts used to configure Linux-based containers are specified in the **clab.node_config** dictionary. The dictionary keys must be *initial* (for initial device configuration), configuration modules, or custom configuration templates (for example, *bgp.session*). The dictionary values are the target file names within the container file system (the file name can be empty for host-side scripts), optionally followed by a suffix indicating the type of the configuration script:

* `:sh` for scripts executed within the containers
* `:ns` for scripts executed within the container network namespace on _netlab_ host (see also [](dev-clab-ns)).

_netlab_ assumes that the modules specified in the **clab.node_config** dictionary are configured through Linux scripts or configuration files. It therefore excludes them from the Ansible playbook executed by the **netlab initial** command.

```{warning}
The scripts specified in the **clab.node_config** dictionary are executed in the order in which they're defined. This order must match the sequence in which the configuration modules must be configured.
```

You can also use **clab.config_mode** device parameter to specify the execution mode (`sh` or `ns`) that applies to all configuration scripts. When a device has that parameter set, the **clab** provider module automatically populates the **node_config** dictionary with all modules and custom templates used on the node that are not already specified in **daemon_config** or **node_config** dictionary.

For example, the following definition was used in the `linux` device in release 25.12 to configure Linux containers with host-side scripts executed in the container network namespace:

```
clab:
  node_config:
    initial: :ns
    lag: :ns
    vlan: :ns
    routing: :ns
```

The **clab.config_mode parameter** can be used to replace these definitions with a simpler one:

```
clab:
  config_mode: ns
```

The **clab.node_config** dictionary is copied into the **clab.config_templates** dictionary (**daemon_config** dictionary takes precedence). The templates specified in the **node_config** dictionary are thus rendered into `clab_files` during the **netlab up**/**netlab create** process (using the standard template search process) and mapped into the container file system through **clab.binds**.

**netlab initial** (also invoked as the last step in the **netlab up** process) executes scripts specified in the **clab.node_config** dictionary:

* Scripts with `:sh` suffix are executed with **docker exec _container_ _script_** command. The scripts should therefore include the shebang interpreter directive on the first line.
* Scripts with `:ns` suffix are executed with **sudo ip netns exec _namespace_ sh _script_**
* Other scripts are treated like configuration files and are not executed.

The Linux scripts are executed before **netlab initial** executes the Ansible playbook.

(change-search-paths)=
## Changing and Troubleshooting Search Paths

The directory and filename search paths used by the **netlab initial** and **netlab config** commands are defined in the **paths** dictionary within the [system defaults](topo-defaults). You can change these parameters or prepend/append another list to them:

* To change a search path list, set the corresponding **defaults.paths** variable in lab topology or user defaults.
* To prepend a list of path components to a search path list, set the **defaults.paths.prepend._path_name_** list.
* To append a list of path components to a search path list, set the **defaults.paths.append._path_name_** list.

For example, to append the `~/templates` directory to the custom configuration template search list, set the **defaults.paths.append.custom.dirs** parameter to `[ ~/templates ]`.

```{warning}
_netlab_ does not report errors in **‌defaults** settings. Make sure you're using the expected attribute paths and list values (not strings).
```

You can inspect the default value of any search path with the **netlab show defaults paths._path_name_** command. For example, to inspect the directory search path used for custom configuration templates, use the **netlab show defaults paths.custom.dirs** command:

```
$ netlab show defaults paths.custom.dirs

netlab default settings within the paths.custom.dirs subtree
=============================================================================

- 'topology:'
- .
- ~/.netlab
- package:extra
```

The filename search patterns can use Jinja2 expressions that reference [Ansible variables](deploy-ansible-variables) set during configuration deployment. Directory search patterns can use these prefixes:

| Prefix | Meaning |
|--------|---------|
| `package:` | **networklab** package (system file) |
| `topology:` | Directory containing the current lab topology |

The directory search patterns are evaluated during the [data transformation process](../transform.md), and the absolute paths are stored in the Ansible inventory (in the **all** group) and the `netlab.snapshot.pickle` file. You can use the **netlab inspect defaults.paths** command to display the transformed values (**netlab inspect** command is available after starting the lab or executing the **netlab create** command).

For example, the default custom configuration template directory  search path (**defaults.paths.custom.dirs**) contains these entries:

```
custom:                         # Custom configuration templates
  dirs:                         # ... search directories
  - "topology:"
  - "."
  - "~/.netlab"
  - "package:extra"
```

The evaluated search path that is stored in `netlab.snapshot.pickle` might contain these values (the topology directory is equal to the current directory, **netlab** is executed from the local Git directory):

```
$ netlab inspect defaults.paths.custom.dirs
- /home/user/BGP/session/2-asoverride
- /home/user/.netlab
- /home/user/net101/tools/netsim/extra
```

You can also display the evaluated absolute paths without creating a lab topology. Use the **evaluate-paths** option of the **netlab show defaults** command:

```
$ netlab show defaults paths.custom.dirs --evaluate-paths

netlab default settings within the paths.custom.dirs subtree
=============================================================================

- /home/user/net101/tools/netsim/cli
- /home/user
- /home/user/.netlab
- /home/pipi/net101/tools/netsim/extra
```

```{tip}
The lab topology is the first entry in the custom template search path. The empty topology file used by the **‌netlab show defaults** resides in the `package:cli` directory, resulting in the first entry in the evaluated paths display.
```
