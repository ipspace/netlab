# Adding Custom External Tools to _netlab_

Some user might want to use _netlab_ with external management tools (example: Graphite, SuzieQ, Prometheus...). _netlab_ distribution includes a [small selection of tools](extools-list); this document describes how you can define additional tools.

External tools are defined in **defaults.tools** dictionary. Tool names are dictionary keys; dictionary values are tool definitions.

You can set **defaults.tools._name_** parameter in a lab topology to use a custom tool with your lab, or set **tools._name_** parameter in [user defaults file](../defaults) to use a tool across multiple labs.

Each tool definition must contain the following parameters:

* **runtime**: default runtime environment (example: *docker*) 
* **config**: a list of actions needed to create configuration files
* For every runtime environment, commands used to start and stop the tool.

A tool definition could contain any number of extra parameters used in the tool configuration templates or tool management commands.

## Configuration files

Tool configuration files are created in tool-specific subdirectory of the current lab directory. For example, the *suzieq* configuration files are created in the *suzieq* directory.

```{warning}
_netlab_ does not map configuration files to container mount points; you have to use the `-v` parameter of **‌docker run** command (or equivalent if you're using a different container orchestration tool) to map them into the tool container.
```

Tool-specific configuration files are created during the **netlab create** process using **tools** output module (which becomes another default output module to use with **netlab create** or **netlab up**).

The **tools** output module iterates over the list of tools used by the current topology and executes actions specified in tool-specific **config** list. Every entry in that list must contain the **dest** parameter (destination file name) and one of the following parameters:

* **template** -- filename of the source Jinja2 template.
* **render** -- the name of the custom format recognized by the tool-specific Python module (example in `netsim/tools/graphite.py`)

```{tip}
* The template file for a tool included with _netlab_ must be in the `netsim/tools/_toolname_` directory. Template files for user-defined tools can be in `tools/_toolname_` directory within the lab directory or user's home directory
* The value of the **render** parameter is passed to the tool-specific module and can be used to create different configuration files.
```

The following definition[^SQPV] creates SuzieQ inventory file `suzieq/suzieq-inventory.yml` using `netsim/tools/suzieq/suzieq.inventory.j2` template from the `networklab` Python package:

```
runtime: docker     # Default: start SuzieQ in a Docker container
config:
- dest: suzieq-inventory.yml
  template: suzieq.inventory.j2
```

[^SQPV]: The value of **defaults.tools.suzieq**  parameter read from `netsim/tools/suzieq.yml` file

Similarly, the following definition[^GFPV] creates Graphite configuration file using `netsim.tools.graphite` module:

```
runtime: docker     # Default: start in a Docker container
config:
- dest: graphite-default.json
  render: graphite
```

[^GFPV]: The value of **defaults.tools.graphite**  parameter read from `netsim/tools/graphite.yml` file

### Using Topology Values in Configuration File Templates

* The Jinja2 configuration file templates can use any lab topology parameter (example: use `{{ name }}` to get lab topology name); use **netlab create -o yaml** to display the transformed topology data structure.
* Device group variables (example: **ansible_connection** or **ansible_ssh_user**) are copied into the node data for easier access. You can use these variables to generate access credentials, for example:

```
---
sources:
- name: netlab_ssh
  hosts:
{% for nn,nd in nodes.items() if nd.ansible_connection == 'network_cli' %}
  - url: ssh://{{ nd.ansible_user }}:{{ nd.ansible_ssh_pass }}@{{ 
            nd.ansible_host }}:{{ nd.ansible_ssh_port or '22' }}/
{% endfor %}
```

* Tool parameters are available as _toolname_._parametername_. For example, to access SuzieQ parameter X, use `{{ suzieq.X }}`.
* Jinja2 templates are executed within *netlab* environment where all variables are Python Boxes. **default** filter does not work; the default value of every undefined variable is an empty dictionary. Use **or** (example: `nd.ansible_ssh_port or '22'`) instead of **default** filter. 

## Tool Management Commands

The commands that have to be executed to start, stop, or connect to the tool are defined in runtime-specific dictionary that can have the following keys:

* **up** -- command(s) executed as the last step of **netlab up** process to start the tool
* **message** -- text message to display after the **up** commands have been executed, or if **netlab connect** is used on a tool that has no **connect** command.
* **down** -- command(s) executed as the first step of **netlab down** process to stop the tool
* **connect** -- command(s) executed by **netlab connect** command to connect to the tool.
* **cleanup** -- command(s) executed during **netlab down --cleanup** to cleanup tool-specific data (example: delete Docker volumes).

Each one of these parameters can be a string (execute a single command) or a list of one or more commands.

### Using Topology Variables in Tool Commands

Each command is evaluated as a Python f-string using transformed topology data as the variables used in the f-string, allowing you to use (for example) `{name}_tool` as the name of lab-specific Docker container. _netlab_ does no further processing of the commands; they have to include all the necessary parameters to map configuration files to containers or expose container ports.

For example, the following dictionary[^SQPV] defines commands needed to start or stop SuzieQ:

```
runtime: docker     # Default: start in a Docker container
docker:
  up:
    docker run --rm -itd --name '{name}_suzieq'
      {sys.docker_net}
      -v '{name}_suzieq':/parquet
      -v './suzieq':/suzieq
      netenglabs/suzieq-demo -c 'sq-poller -I /suzieq/suzieq-inventory.yml'
  connect:
    docker exec -it '{name}_suzieq' /usr/local/bin/suzieq-cli
  down:
    docker kill '{name}_suzieq'
  cleanup:
    docker volume rm '{name}_suzieq'
```

**Notes:**
* The **up** command uses **docker run** to start the container and maps SuzieQ configuration directory and a lab-specific volume into container mount points. The `sys.docker_net` parameter is explained in the next section.
* SuzieQ container executes **bash** as the default command. Parameters of **docker run** command are therefore Bash parameters.
* **connect** command uses **docker exec** to execute another command in the same container (start SuzieQ CLI).
* **docker exec** command specifies the full path to the **suzieq-cli** command because the default path in the SuzieQ container does not include `/usr/local/bin`.
* **cleanup** command deletes the volume created with the **docker run** command.

### Running External Tools with Lab Containers

External tools have to be connected to the same Docker network as the management interface of the lab containers. The default name of that network is `netlab_mgmt` but it can change if you use [multilab plugin](../plugins/multilab.md).

_netlab_ prepares the `--network=_name_` parameter that you have to include with the **docker run** in the `sys.docker_net` topology variable. Include `{sys.docker_net}` parameter in any **docker run** command if you want your containers to communicate with the lab devices over the management network.

### Removing Tool Configuration Directory

**netlab down --cleanup** removes the tool configuration directories, but fails to do so if the container creates additional files in that directory -- containers are often run as user **root**, and a regular user cannot remove files created by another user.

If your tool creates additional files in the tool configuration directory, add **sudo rm -fr *toolname*** as one of the **cleanup** commands.
