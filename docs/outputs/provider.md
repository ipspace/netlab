# Virtualization Provider Output Module

*provider* output module creates virtualization provider (*vagrant/libvirt* or *containerlab*) configuration file. 
It is invoked automatically during the **[netlab up](netlab-up)** process, but if you need to troubleshoot it, use the **[netlab create -o provider](netlab-create)** command[^1].

The *provider* output module can take an optional destination file name (`-` meaning *stdout*) and takes no formatting modifiers. The default destination file name is derived from the virtualization provider settings (`Vagrantfile` for Vagrant, `clab.yml` for containerlab).

[^1]: **netlab create** also invokes the *provider* output module when no output formats are specified in the **netlab create** command.
