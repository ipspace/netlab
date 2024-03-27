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

(linux-forwarding)=
## Packet Forwarding on Linux Hosts

IPv4 and IPv6 packet forwarding on Linux devices is controlled with the **role** node parameter:

* **host** (default): a Linux device does not perform packet forwarding and cannot be the default gateway for other hosts.
* **gateway**: a Linux device does not perform packet forwarding but acts as the default gateway for other hosts. You will have to install a proxy (or a similar solution) for inter-subnet packet forwarding.
* **router**: A Linux device performs packet forwarding but does not run routing protocols. Use **frr** or **cumulus** device if you want to run routing protocols on a Linux server.

(linux-loopback)=
## Loopback Interface

_netlab_ does not configure a global loopback IP address on Linux nodes with **role** set to **host** (the default _netlab_ setting).

A loopback IP address is [allocated](../example/addressing-tutorial.md#loopback-addresses) to a Linux node if you set **role** to any other value, and the initial configuration script configures an additional IP address on the **lo** interface, for example:

```
vagrant@host:~$ ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet 10.0.0.1/32 scope global lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 08:4f:a9:00:00:01 brd ff:ff:ff:ff:ff:ff
    inet 192.168.121.101/24 brd 192.168.121.255 scope global dynamic eth0
       valid_lft 3587sec preferred_lft 3587sec
    inet6 fe80::a4f:a9ff:fe00:1/64 scope link
       valid_lft forever preferred_lft forever
3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether 52:54:00:50:03:5a brd ff:ff:ff:ff:ff:ff
    inet 10.1.0.1/30 brd 10.1.0.3 scope global eth1
       valid_lft forever preferred_lft forever
    inet6 fe80::5054:ff:fe50:35a/64 scope link
       valid_lft forever preferred_lft forever
```

(linux-lldp)=
## LLDP

LLDP is started on Ubuntu virtual machines if the **netlab_lldp_enable** group variable is set to **True** (default setting is **False**). LLDP is not started in Linux containers or in non-Ubuntu Linux virtual machines.

To enable LLDP on Ubuntu virtual machines, set the **netlab_lldp_enable** node parameter or **defaults.devices.linux.group_vars.netlab_lldp_enable** variable to **True**.

(linux-dhcp-relay)=
## DHCP Relaying on Linux

DHCP relaying on Ubuntu and Cumulus Linux uses `isc-dhcp-relay`, and is implemented only for IPv4. The `isc-dhcp-relay` has a few limitations:

* The list of DHCP servers is specified per daemon, not per interface. The configuration template combines DHCP servers specified on all interfaces into a single list of servers.
* While it might be possible to run a DHCP relay within a single VRF (for intra-VRF, not inter-VRF relaying), _netlab_ does not implement that. DHCP relaying with `isc-dhcp-relay` does not work between VRF interfaces.

(linux-initial-config)=
## Initial Configuration on Linux Virtual Machines

_netlab_ supports two Linux networking configuration mechanisms:

* Netplan-based configuration on Ubuntu -- used when  the **netlab_linux_distro** group variable is set to **ubuntu** (default setting)
* Traditional configuration with **ip** commands.

You might have to change the initial configuration mechanism to *traditional configuration* if you're using Linux virtual machines that are not based on Ubuntu. To do that, set the node **netlab_linux_distro** parameter to **vanilla** or set **defaults.devices.linux._provider_.group_vars.netlab_linux_distro** variable to **vanilla**.

(linux-ubuntu-package)=
## Ubuntu Package Installation During Initial Configuration

If needed the _netlab_ initial configuration script installs **lldpd** and **net-tools** Ubuntu packages.

* **net-tools** package is installed if the **netlab_net_tools** variable is set to **True** (default setting is **False**) and if the **arp** command cannot be found.
* **lldpd** package is installed if the **netlab_lldp_enable** variable is set to **True** (default setting is **False**) and if the **lldpd.service** is not running.

The package installation is performed only when the **netlab_linux_distro** variable is set to **ubuntu** (see [](linux-initial-config))

_netlab_ initial configuration script will skip Ubuntu package installation if it can find **arp** command or if the **lldpd.service** is already running, allowing you to build custom Vagrant boxes that require no Internet access during the initial configuration.

(clab-linux)=
## Initial Configuration on Linux Containers

The initial configuration process (**[netlab initial](../netlab/initial.md)**) does not rely on commands executed within Linux containers:

* The `/etc/hosts` file is generated during the **[netlab create](../netlab/create.md)** process from the ```templates/provider/clab/frr/hosts.j2``` template (see [](clab-config-template)).
* Interface IP addresses and static routes to default gateway (see [](linux-routes)) are configured with **ip** commands executed on the Linux host but within the container network namespace.
* Static default route points to the management interface.

You can therefore use any container image as a Linux node.