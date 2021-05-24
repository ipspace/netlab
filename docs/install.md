# Installation

If you'd like to use *netsim-tools* with *libvirt*[^1], and don't have a bare-metal Ubuntu server, you might want to follow the [tutorial created by Leo Kirchner](https://blog.kirchne.red/netsim-tools-quickstart.html). 

[^1]: The *libvirt* Vagrant plugin starts all network devices in parallel, resulting in much faster lab setup than using Vagrant with Virtualbox.

If you want to install *netsim-tools* and all its dependencies on an existing Ubuntu server (bare-metal or VM), [use the Ansible playbook provided in the distribution](labs/libvirt.md#prerequisite-software-installation).

In all other cases:

* Clone the [netsim-tools Github repository](https://github.com/ipspace/netsim-tools) (or the [netsim-examples repository](https://github.com/ipspace/netsim-examples/) which includes netsim-tools repository as a submodule.
* If needed, select the desired release with **git checkout _release-tag_**. Use **git tag** to get the list of release tags.
* Within the **netsim-tools** directory, install PyYAML, Jinja2, netaddr and python-box Python libraries with **pip3 install -r requirements.txt**.
* Optional: install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). The tools were tested with Ansible 2.9 and 2.10.
* Add **netsim-tools** directory to your PATH

## Building the Lab Environment

```eval_rst
.. toctree::
   :maxdepth: 1

   labs/libvirt.md
   labs/virtualbox.md
   labs/clab.md
```
