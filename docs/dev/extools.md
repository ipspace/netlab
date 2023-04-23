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

The **tools** output module iterates over the list of tools used by the current topology and executes actions specified in tool-specific **config** list. Every entry in that list must contain the following parameters:

* **dest** -- destination file name
* **template** -- the name of the source Jinja2 template.

```{tip}
The template file for a tool included with _netlab_ must be in the `netsim/tools/_toolname_` directory. Template files for user-defined tools can be in `tools/_toolname_` directory within the lab directory or user's home directory
```

The following definition (the value of **defaults.tools.suzieq**  parameter read from `netsim/tools/suzieq.yml` file) creates SuzieQ inventory file `suzieq/suzieq-inventory.yml` using `netsim/tools/suzieq/suzieq.inventory.j2` template from the `networklab` Python package:

```
runtime: docker     # Default: start SuzieQ in a Docker container
config:
- dest: suzieq-inventory.yml
  template: suzieq.inventory.j2
```

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
            nd.ansible_host }}:{{ nd.ansible_ssh_port or '22' }}/ devtype={{ nd.ansible_network_os }}
{% endfor %}
```

* Tool parameters are available as _toolname_._parametername_. For example, to access SuzieQ parameter X, use `{{ suzieq.X }}`.
* Jinja2 templates are executed within *netlab* environment where all variables are Python Boxes. **default** filter does not work; the default value of every undefined variable is an empty dictionary. Use **or** (example: `nd.ansible_ssh_port or '22'`) instead of **default** filter. 

## Tool Management Commands

The commands that have to be executed to start, stop, or connect to the tool are defined in runtime-specific dictionary that can have the following keys:

* **up** -- a command or a list of commands executed as the last step of **netlab up** process to start the tool
* **down** -- a command or a list of commands executed as the first step of **netlab down** process to stop the tool
* **connect** -- a command or a list of commands executed by **netlab connect** command to connect to the tool.
* **cleanup** -- a command or a list of commands executed during **netlab down --cleanup** to cleanup tool-specific data (example: delete Docker volumes).

Each command is evaluated as a Python f-string using transformed topology as the data to be used in the f-string, allowing you to use (for example) `{name}_tool` as the name of lab-specific Docker container. _netlab_ does no further processing of the commands; they have to include all the necessary parameters to map configuration files to containers or expose container ports.

Example: the following dictionary (the value of **defaults.tools.suzieq**  parameter read from `netsim/tools/suzieq.yml` file) defines commands needed to start or stop SuzieQ:

```
runtime: docker     # Default: start in a Docker container
docker:
  up:
    docker run --rm -itd --name '{name}_suzieq'
      -v '{name}_suzieq':/home/suzieq/parquet
      -v './suzieq':/suzieq
      netenglabs/suzieq-demo -c 'sq-poller -I /suzieq/suzieq-inventory.yml'
  connect:
    docker exec -it '{name}_suzieq' /usr/local/bin/suzieq-cli
  down:
    docker kill '{name}_suzieq'
  cleanup:
    docker volume rm '{name}_suzieq'
```

Notes:
* The **up** command maps SuzieQ configuration directory and a lab-specific volume into container mount points.
* SuzieQ container executes **bash** as the default command. Parameters of **docker run** command are therefore Bash parameters.
* **connect** command uses **docker exec** to execute another command in the same container (start SuzieQ CLI).
* **docker exec** command specifies the full path to the **suzieq-cli** command because the default path in the SuzieQ container does not include `/usr/local/bin`.
* **cleanup** command deletes the volume created with the **docker run** command.
