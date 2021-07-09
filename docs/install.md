# Installation

*netsim-tools* is available as a Python3 package that runs on most systems supporting Python3. It's been tested with Python 3.9, but should run on older Python3 versions. 

The lab control functionality uses Ansible playbooks, and thus works only on systems supported by Ansible. It's recommended to use Ansible 2.9 or higher.

## Installing a Python Package

Use `python3 -m pip install netsim-tools` to install the software. The installation process will install all prerequisite Python packages (but not Ansible) and create the **netlab** command.

## Installing from GitHub

* Clone the [netsim-tools Github repository](https://github.com/ipspace/netsim-tools).
* If needed, select the desired release with **git checkout _release-tag_**. Use **git tag** to get the list of release tags.
* Within the **netsim-tools** directory, install prerequisite Python packages with **python3 -m pip install -r requirements.txt**.
* Optional: install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). 
* Add **netsim-tools** directory to your PATH with **source setup.sh** command

## Complete Ubuntu VM/Server Installation

If you'd like to use *netsim-tools* with *libvirt*[^1], and would like to create a Ubuntu VM from scratch, follow the [tutorial created by Leo Kirchner](https://blog.kirchne.red/netsim-tools-quickstart.html). 

[^1]: The *libvirt* Vagrant plugin starts all network devices in parallel, resulting in much faster lab setup than using Vagrant with Virtualbox.

If you want to install *netsim-tools* and all its dependencies on an existing Ubuntu server (bare-metal or VM):

* If needed, install **pip** with `sudo apt-get update && sudo apt-get install -y python3-pip`
* Install *netsim-tools* package[^1] with `sudo python3 -m pip install netsim-tools`
* Install additional software with `netlab install ubuntu ansible libvirt` command ([more details](netlab/install.md))

[^1] Yes, I know one should install Python packages into a virtual environment, but hopefully we're either talking about a throwaway VM, or you know what you're doing.

## Building the Lab Environment

```eval_rst
.. toctree::
   :maxdepth: 1

   labs/libvirt.md
   labs/virtualbox.md
   labs/clab.md
```
