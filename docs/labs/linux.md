# Generic Linux Devices

You can run Linux hosts or routers in virtual machines or containers. The default image used for a Linux virtual machine is Ubuntu 20.04, the default container image is Python 3.9 container running on Alpine Linux.

To use any other Linux distribution or container, or to start a home-built Vagrant box or Docker container, add **image** attribute with the name of Vagrant box or Docker container to the node data[^GL]. The only requirements for a Linux virtual machine is working Python environment (to support Ansible playbooks used in **netlab initial** command) and the presence of **ip** command used in initial device configuration. Docker containers have no requirements ([see below](clab-linux))

```eval_rst
.. contents:: More Details
   :depth: 2
   :local:
   :backlinks: none
```

[^GL]: You can also set the **defaults.devices.linux._provider_.image** attribute to change the Vagrant box or Docker container for all Linux hosts in your lab.

(linux-routes)=
## Host Routing

Generic Linux device is an IP host that by default does not support IP forwarding or IP routing protocols. It uses static routes set up as follows:

* IPv4 default route points to Vagrant- or containerlab management interface (set by Vagrant/DHCP or containerlab).
* IPv6 default route points to whichever adjacent device is sending IPv6 Route Advertisement messages (default Linux behavior).
* IPv4 static routes for all IPv4 address pools defined in lab topology point to the subnet default gateway on the first non-management interface.

The default gateway on a subnet is set by the [gateway module](../module/gateway.md). If you're not using that module, _netlab_ sets the default gateway to the interface IP address of the first non-host[^NH] device connected to the subnet.

[^NH]: A device that does not have **role** set to **host**. A Linux node is usually a **host** and cannot be used as a default gateway.

## Packet Forwarding on Linux Hosts

_netlab_ disables IPv4 and IPv6 packet forwarding on Linux devices<!-- with **role** set to **host** or **gateway**-->.

(linux-lldp)=
## LLDP

LLDP is started on Ubuntu virtual machines if the **netlab_lldp_enable** group variable is set to **True** (default setting). LLDP is not started in Linux containers or in non-Ubuntu Linux virtual machines.

To disable LLDP on Ubuntu virtual machines, set the **netlab_lldp_enable** node parameter or **defaults.devices.linux.group_vars.netlab_lldp_enable** variable to **False**.

(linux-initial-config)=
## Initial Configuration on Linux Virtual Machines

_netlab_ supports two Linux networking configuration mechanisms:

* Netplan-based configuration on Ubuntu -- used when  the **netlab_linux_distro** group variable is set to **ubuntu** (default setting)
* Traditional configuration with **ip** commands.

You might have to change the initial configuration mechanism to *traditional configuration* if you're using Linux virtual machines that are not based on Ubuntu. To do that, set the node **netlab_linux_distro** parameter to **vanilla** or set **defaults.devices.linux._provider_.group_vars.netlab_linux_distro** variable to **vanilla**.

## Ubuntu Package Installation During Initial Configuration

If needed the _netlab_ initial configuration script installs **lldpd** and **net-tools** Ubuntu packages.

* **net-tools** package is installed if the **netlab_net_tools** variable is set to **True** (default setting) and if the **arp** command cannot be found.
* **lldpd** package is installed if the **netlab_lldp_enable** variable is set to **True** (default setting) and if the **lldpd.service** is not running.

The package installation is performed only when the **netlab_linux_distro** variable is set to **ubuntu** (see [](linux-initial-config))

_netlab_ initial configuration script will skip Ubuntu package installation if it can find **arp** command or if the **lldpd.service** is already running, allowing you to build Vagrant boxes that require no Internet access during the initial configuration.

You can also disable package installation by setting **netlab_net_tools** and **netlab_lldp_enable** node parameters or corresponding **defaults.devices.linux.group_vars._variable_** variables to **False**.

(clab-linux)=
## Initial Configuration on Linux Containers

The initial configuration process (**[netlab initial](../netlab/initial.md)**) does not rely on commands executed within Linux containers:

* The `/etc/hosts` file is generated during the **[netlab create](../netlab/create.md)** process from the ```templates/provider/clab/frr/hosts.j2``` template (see [](clab-config-template)).
* Interface IP addresses and static routes to default gateway (see [](linux-routes)) are configured with **ip** commands executed on the Linux host but within the container network namespace.
* Static default route points to the management interface.

You can therefore use any container image as a Linux node.