# netlab Command Reference

The **netlab** command is the *netlab* CLI interface. It includes data model transformations, lab creation and deletion, device configurations with Ansible playbooks, and console connectivity scripts.

## Creating the Lab

* **[netlab up](up.md)** creates configuration files from lab topology, starts the virtual lab, and deploys initial device configurations
* **[netlab down](down.md)** destroys the virtual lab
* **[netlab create](create.md)** creates virtualization provider and network automation configuration files (usually `Vagrantfile`, `hosts.yml` and `ansible.cfg`)
* **[netlab restart](restart.md)** stops and restarts the lab, including lab topology reconfiguration and recreation of configuration files if you changed the lab topology definition.

## Configuring and Controlling the Lab

* **‌[netlab status](status.md)** display the state of lab instances running on the current server
* **[netlab initial](initial.md)** uses an internal Ansible playbook to deploy initial device configurations to lab devices
* **[netlab config](config.md)** creates custom configuration snippets from Jinja2 templates and uses an internal Ansible playbook to deploy them to lab devices
* **[netlab connect](connect.md)** relies on Ansible inventory created with **netlab create** to find IP address, username, and password of specified lab device, and uses SSH or **docker exec** to connect to the lab device.
* **[netlab collect](collect.md)** uses Ansible device facts (or equivalent functionality implemented with Ansible modules) to collect device configurations and store them into specified directory.

## Utility Commands

* **[netlab install](install.md)** installs additional Ubuntu software, Ansible, and libvirt/vagrant.
* **[netlab test](test.md)** tests virtual lab installation
* **[netlab show](show)** displays system settings
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
   netlab initial <initial.md>
   netlab install <install.md>
   netlab restart <restart.md>
   netlab show <show.md>
   netlab status <status.md>
   netlab test <test.md>
   netlab up <up.md>
```

