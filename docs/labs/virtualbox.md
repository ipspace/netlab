# Virtualbox-Based Lab on Windows, MacOS or Linux

Virtualbox-based Vagrant lab is extremely easy to set up on Windows, MacOS, or Linux:

* Install Virtualbox (might require fiddling with BIOS setup on Ubuntu bare-metal installations)
* Install Vagrant
* Create [lab topology file](../topology-overview.md). Use `provider: virtualbox` in lab topology to select the *virtualbox* virtualization provider.
* Use **[netlab create](../netlab/create.md)** script to create *Vagrantfile* and Ansible inventory[^1]
* Execute **vagrant up**

[^1]: Running Ansible on Windows is not supported, but supposedly it runs just fine under WSL. 

## Testing the Installation

The easiest way to test your installation is to use **netlab test** command. If you prefer to do step-by-step tests, or if you don't want to use WSL on Windows, you might find this recipe useful:

* Create an empty directory and `topology.yml` file with the following contents within that directory:

```
---
defaults:
  device: cumulus

nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3, s1-s2-s3 ]
```

* Create Vagrantfile with `netlab create`
* Execute `vagrant up` to spin up three Cumulus VX virtual machines
* Connect to the Cumulus VX devices with `vagrant ssh`
* Destroy the lab with `vagrant destroy -f`

## Creating Vagrant Boxes

Vagrant relies on *boxes* (prepackaged VM images). The only image currently available on Vagrant Cloud is the Cumulus VX image -- Vagrant automatically downloads it whenever you use Cumulus VX in your lab topology.

You'll have to download Arista vEOS and Nexus 9300v images from the vendor web site and install them with **vagrant box add _filename_ \-\-name _boxname_** command

The Vagrant boxes should have the following names:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Arista vEOS            | arista/veos        |
| Cisco Nexus 9300v      | cisco/nexus9300v   |
| Cumulus VX             | CumulusCommunity/cumulus-vx |

**Notes**:

* If you want to add other network devices, build your own Vagrant boxes and modify *topology-defaults.yml* file (search for **eos:** or **nxos:** keys to see how to set up devices that work with multiple virtualization providers). 
* The latest version of Arista vEOS available as Vagrant box for VirtualBox is 4.21.14M. You'll have to build your own box if you want to have a more recent EOS version.
* Vagrantfile created by **netlab create** sets up port forwarding for SSH (22), HTTP (80) and NETCONF (830), but the corresponding Ansible inventory contains only **ansible_port** (SSH). You could edit the final inventory by hand, add extra file to `host_vars`, or fix _netsim-tools_ code. Should you decide to do the latter, please contact us in advance to discuss the necessary data structures.
