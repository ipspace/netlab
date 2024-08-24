(tutorial-linux)=
# Add Linux Hosts to Lab Topologies

It's straightforward to add Linux hosts to _netlab_ topologies and deploy the software you want to test (management software, network services daemons, traffic generators, etc.) on the Linux hosts. This tutorial will help you get started.

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
```

## Adding Linux Hosts

To add Linux hosts to a lab topology, add nodes with **device: linux**. Although it's possible to have Linux nodes with multiple interfaces, keep things simple and connect these nodes to a single link.

The Linux hosts will be started as virtual machines if you use the *libvirt* or *virtualbox* provider or as containers if you use the *clab* provider. You can also [add Linux containers to a *libvirt* topology](labs-multi-provider): add **provider: clab** to node data.

For example, the following topology starts two Linux containers attached to a Juniper vPTX virtual machine:

```
provider: libvirt

nodes:
  rtr:
    device: vptx
  h1:
    device: linux
    provider: clab
  h2:
    device: linux
    provider: clab

links: [ rtr-h1, rtr-h2 ]
```

## Configuring Linux Hosts

*netlab* uses Ansible to configure Linux virtual machines; you have to use a Vagrant box that contains a working Python installation. *netlab* assumes the Linux virtual machines run Ubuntu and uses *netplan* to configure VM interfaces ([more details](linux-initial-config)). To use the traditional **ip** commands on other Linux distributions, add **‌netlab_linux_distro: vanilla** to node data.

Linux containers are configured with host commands executed within the container networking namespace. _netlab_ does not expect to have Python (or any other CLI command) in a Linux container; you can use whatever Linux container you wish.

On Linux hosts, the _netlab_ initial configuration process adds the `/etc/hosts` file, configures IP addresses on management and lab interfaces, installs LLDP and `net-tools` on Ubuntu virtual machines, and creates static routes pointing to the first-hop gateway on the first lab interface ([more details](linux-routes)). The default route (managed by Vagrant or containerlab) always points to the management interface, allowing you to connect to the Internet and install additional software on Linux hosts.

## Custom Containers or Virtual Machines

*netlab* starts Ubuntu 20.04 Vagrant boxes when you add Linux virtual machines to a lab topology and Python/Alpine containers when you add Linux containers to a lab topology.

```{tip}
The defaults might change in a future _netlab_ release. Use **‌netlab show images -d linux** to display the current default values.
```

You can change the Vagrant box or container image for any node in the lab topology with the **image** node parameters.

For example, to add a Linux container running Cisco's TRex traffic generator in a [Docker container](https://hub.docker.com/r/trexcisco/trex), set the **image** to **trexcisco/trex**, for example:

```
provider: libvirt

nodes:
  rtr:
    device: vptx
  h1:
    device: linux
    provider: clab
    image: trexcisco/trex

links: [ rtr-h1, rtr-h2 ]
```

## Installing Custom Linux Software

If you want to install custom Linux software into a Linux host after the lab has been started, start with a generic Linux distribution (for example, `generic/ubuntu2004` Vagrant box or `ubuntu:24.04` container).

```{warning}
Ubuntu Vagrant boxes after Ubuntu 20.04 are broken; they cannot find any interface apart from the management interface (`eth0`). If you want to work with a recent Ubuntu distribution, use Linux containers.
```

After the lab has been started, log into the Linux host and install the software, for example[^US]:

[^US]: You'll have to use the **sudo** command on a Linux VM.

```
# apt-get update
# apt-get install rsyslog
```

Start the software, for example:

```
# rsyslogd
```

Congratulations, you added a *syslog* server to your lab.

Once you've mastered the installation process, collect the installation commands into a configuration template, such as `syslogd.j2`. The configuration template name should end with `.j2`, and the first line should be `#!/bin/bash` to tell the _netlab_ device configuration Ansible playbook to start a Bash script on your Linux host. For example, this configuration template installs and starts syslog daemon[^YAG]:

[^YAG]: The `-y` option of the `apt-get` command tells the APT installer to install the software without further questions.

```
#!/bin/bash
apt-get update
apt-get install rsyslog -y
rsyslogd
```

Finally, add the [custom configuration template](custom-config) to your Linux host with the **config** parameter:

```
defaults.device: eos
provider: clab

nodes:
  r:
  h:
    device: linux
    image: ubuntu:24.04
    config: [ syslogd ]
```

Now, you can start the lab, and the lab configuration process (**[netlab initial](netlab-initial)**) will install the syslog daemon on the Linux host.
