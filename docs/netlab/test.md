# Test Virtual Lab Installation

**netlab test** libvirt- or VirtualBox-based virtual lab installation. It creates a simple virtual lab using Cumulus VX, starts the lab, deploys initial configurations, destroys the lab, and cleans up.

## Usage

```text
usage: netlab test [-h] [-w WORKDIR] [-v] {libvirt,virtualbox,clab}

Test virtual lab installation

positional arguments:
  {libvirt,virtualbox,clab}
                        Run tests for the specified provider

optional arguments:
  -h, --help            show this help message and exit
  -w WORKDIR, --work-directory WORKDIR
                        Working directory (default: test)
  -v, --verbose         Verbose logging
```

## Testing Procedure

**netlab test** command:

* Checks whether the selected virtualization provider and Vagrant are installed;
* Creates a working directory and copies sample lab topology containing three routers and a few links into that directory;
* Uses **netlab create** to create Vagrantfile, Ansible inventory, and `ansible.cfg`.
* Starts the lab with **vagrant up**. Cumulus VX boxes are downloaded on demand if needed.
* Deploys initial device configurations and configure OSPF with **netlab initial**.
* Destroys the lab with **vagrant destroy -f**
* Cleans up the working directory

## Notes on Containerlab Tests

* *containerlab* tests start Cumulus VX containers in *Docker* mode (container, not a micro-VM) and thus test the *containerlab* but not *firecracker* or *KVM* functionality.
* See [Platform Support](../platforms.md) for more details on Cumulus VX running under *containerlab*.
