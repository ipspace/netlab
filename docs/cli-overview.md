# CLI Overview

The following programs, scripts and Ansible playbooks are included with *netlab* and available as a subcommand of **netlab** command.

## Creating and Destroying the Lab

**netlab up**
: Uses **netlab create** to create configuration files, starts the virtual lab, and uses **netlab initial** to deploy initial device configurations. [More details...](netlab/up.md)

**netlab down**
: Destroys the virtual lab. [More details...](netlab/down.md)

**netlab create**
: Creates a full-blown network topology, Vagrantfile and Ansible inventory from a simple list of nodes and links. [More details...](netlab/create.md)

## Deploying Device Configuration

**netlab initial**
: Configures common device parameters using topology data generated by **netlab create** and default device configuration templates. Configured parameters include hostname, LLDP, interface admin state, MAC and IP addresses, and optional routing protocols. [More details...](netlab/initial.md)

## Working with Lab Devices

**netlab connect**
: Use Ansible inventory connect to a lab device using its inventory name. Device IP address (**ansible_host**) and username/passwords are retrieved from Ansible inventory. Ideal when you use centralized Vagrant environments and want to connect to the devices while being in playbook development directory. [More details...](netlab/connect.md)

**netlab config**
: Applies any set of custom Jinja2 configuration templates to network devices. Includes support for platform-specific configuration templates. [More details...](netlab/config.md)

**netlab collect**
: Using Ansible fact gathering or other device-specific Ansible modules, collects device configurations and saves them in specified directory. [More details...](netlab/collect.md)