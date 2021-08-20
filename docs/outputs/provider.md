# Virtualization Provider Output Module

*provider* output module creates virtualization provider (*vagrant/libvirt*, *vagrant/virtualbox* or *containerlab*) configuration file. It's invoked by specifying `-o provider` parameter in **netlab create** command[^1].

The *provider* output module can take an optional destination file name (`-` meaning *stdout*) and takes no formatting modifiers. Default destination file name is derived from the virtualization provider settings (`Vagrantfile` for Vagrant, `clab.yml` for containerlab).

[^1]: **netlab create** also invokes the *provider* output module when no output formats are specified in the **netlab create** command.
