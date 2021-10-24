# Start Virtual Lab

**netlab up** is a high-level command that uses other **netlab** commands to:

* Create virtualization provider configuration files;
* Create network automation configuration files;
* Check the virtualization provider installation;
* Start the virtual lab;
* Deploy initial device configurations.

## Usage

**netlab up [ _topology-file_ ]**

## Provider-Specific Initialization

When used with *libvirt* provider, **netlab up** changes the `group_fwd_mask` for all Vagrant-created Linux bridges to [enable LLDP passthrough](https://blog.ipspace.net/2020/12/linux-bridge-lldp.html).
