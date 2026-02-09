# Ansible Inventory Output Module

*ansible* output module creates Ansible inventory (*hosts.yml*, *host_vars*, and *group_vars*) and Ansible configuration file (*ansible.cfg*) file. It's invoked by specifying `-o ansible` parameter in **netlab create** command[^1].

The *provider* output module can take one or two optional destination file names separated by a comma. The first file name specifies Ansible inventory file (default: *hosts.yml*), the second one Ansible configuration file (default: *ansible.cfg*)

A single formatting modifier can be used to modify the distribution of information between *hosts.yml*, *host_vars* and *group_vars*:

* **min** -- Ansible inventory file contains all known host- and group information. *host_vars* and *group_vars* are not created[^2].
* **dirs** (default) -- Ansible inventory file contains minimal amount of information[^3]. Host- and group directories are created under *host_vars* and *group_vars*. Each host- or group directory within *host_vars* or *group_vars* contain *topology* file in JSON or YAML format (see below) with host- or group variables. This format allows you to add Ansible inventory information (create additional files within host- or group subdirectories) without interfering with *ansible* output module.
* **files** -- Ansible inventory file contains a minimal amount of information. Per-host or per-group files are created in *host_vars* and *group_vars*. Do not modify those files; they will be overwritten the next time you run **netlab create** command.

The same parameter can be set using the **defaults.outputs.ansible.hostvars** [topology default](topo-defaults).

The Ansible inventory files (apart from `hosts.yml`) are created in JSON format. If you need YAML-formatted inventory files, set the **defaults.outputs.ansible.filetype** [topology default](topo-defaults) to `yaml` or `yml` (depending on the desired file type).

[^1]: **netlab create** also invokes the *provider* output module when no output formats are specified in the **netlab create** command.

[^2]: Existing *host_vars* and *group_vars* directories are not removed. Make sure you won't get information overload when trying out different Ansible inventory formats.

[^3]: Node **id** and IP address (**ansible_host**)