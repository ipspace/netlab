# netlab Command Reference

The **netlab** command is the *netlab* CLI interface. It includes data model transformations, lab creation and deletion, device configurations with Ansible playbooks, reporting, and device console connectivity scripts.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Creating the Lab

* **[netlab up](up.md)** creates configuration files from lab topology, starts the virtual lab, and deploys initial device configurations.
* **[netlab create](create.md)**, usually executed as part of **netlab up** process, creates virtualization provider and network automation configuration files (usually `Vagrantfile`, `hosts.yml` and `ansible.cfg`). It can also be used to create other output formats (graphs, reports, or YAML/JSON printouts).
* **[netlab restart](restart.md)** stops and restarts the lab, including lab topology reconfiguration and recreation of configuration files if you changed the lab topology definition.

## Configuring and Controlling the Lab

* **[netlab connect](connect.md)** uses the transformed lab topology data to find IP address, username, and password of specified lab device or [external tool](../extools.md), and uses SSH or **docker exec** to connect to the lab device/tool.
* **[netlab collect](collect.md)** uses Ansible device facts (or equivalent functionality implemented with Ansible modules) to collect device configurations and store them into specified directory.
* **[netlab down](down.md)** destroys the virtual lab.

## Reports and Graphs

* **‌[netlab status](status.md)** display the state of lab instances running on the current server
* **[netlab report‌](report.md)** creates a report (example: node/link addressing) from the transformed lab topology data.
* **[netlab graph](graph.md)** creates a graph description of physical or BGP topology in Graphviz or D2 format

## Device Configuration Commands

* **[netlab initial](initial.md)** uses an internal Ansible playbook to deploy initial device configurations to lab devices. It's usually executed as part of **netlab up** command.
* **[netlab config](config.md)** creates custom configuration snippets from Jinja2 templates and uses an internal Ansible playbook to deploy them to lab devices. It's usually executed as part of **netlab up** command.

## Utility Commands

* **[netlab install](install.md)** installs additional Ubuntu software, Ansible, and libvirt/vagrant.
* **[netlab test](test.md)** tests virtual lab installation
* **[netlab show](show)** displays system settings

## Provider-Specific Commands

* **netlab libvirt** [builds Vagrant boxes](../labs/libvirt.md#building-your-own-boxes) for *[vagrant-libvirt](../labs/libvirt.md)* provider.
* **[netlab clab](clab.md)** contains containerlab-related utilities

## Individual netlab Commands
<!-- commands come here -->

```eval_rst
.. toctree::
   :maxdepth: 1

   netlab clab <clab.md>
   netlab collect <collect.md>
   netlab config <config.md>
   netlab connect <connect.md>
   netlab create <create.md>
   netlab down <down.md>
   netlab graph <graph.md>
   netlab initial <initial.md>
   netlab install <install.md>
   netlab report <report.md>
   netlab restart <restart.md>
   netlab show <show.md>
   netlab status <status.md>
   netlab test <test.md>
   netlab up <up.md>
```

