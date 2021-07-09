# netlab Command Reference

The **netlab** command is the CLI interface to *netsim-tools* functionality, including data model transformation, Ansible playbooks and device connectivity scripts:

## Creating the Lab

* **[netlab create](create.md)** creates virtualization provider and network automation configuration files (usually `Vagrantfile`, `hosts.yml` and `ansible.cfg`)

## Configuring and Controlling the Lab

* **[netlab initial](initial.md)** uses an internal Ansible playbook to deploy initial device configurations to lab devices
* **[netlab config](config.md)** creates custom configuration snippets from Jinja2 templates and uses an internal Ansible playbook to deploy them to lab devices
* **[netlab connect](connect.md)** relies on Ansible inventory created with **netlab create** to find IP address, username, and password of specified lab device, and uses SSH or **docker exec** to connect to the lab device.
* **[netlab collect](collect.md)** uses Ansible device facts (or equivalent functionality implemented with Ansible modules) to collect device configurations and store them into specified directory.

## Utility Commands

* **[netlab install](install.md)** installs additional Ubuntu software, Ansible, and libvirt/vagrant.
* **[netlab test](test.md)** tests virtual lab installation
* **[netlab alias](alias.md)** creates Bash aliases for old (release 0.7) CLI commands.

## Individual netlab Commands
<!-- commands come here -->

```eval_rst
.. toctree::
   :maxdepth: 1

   netlab alias <alias.md>
   netlab collect <collect.md>
   netlab config <config.md>
   netlab connect <connect.md>
   netlab create <create.md>
   netlab initial <initial.md>
   netlab install <install.md>
   netlab test <test.md>
```
