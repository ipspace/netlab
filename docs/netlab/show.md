# Display System Information

**netlab show** displays system settings in a tabular, text, or YAML format. The command can display system settings (as shipped with the *networklab* package) or system settings augmented with [user defaults](../defaults.md).

The following settings can be displayed:

* **devices** -- Supported devices
* **images** -- Vagrant box names or container names for all supported devices or a single device
* **module** -- Configuration modules
* **module-support** -- Configuration modules support matrix
* **providers** -- Virtualization providers

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Display Supported Devices

```text
usage: netlab show devices [-h] [--system] [--format {table,text,yaml}] [-d DEVICE]

Display supported devices

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -d DEVICE, --device DEVICE
                        Display information for a single device
```

**Examples:**

* Display devices (names and descriptions) supported by _netlab_.

```text
$ netlab show devices
Virtual network devices supported by netlab

+--------------+-----------------------------------------------+
| device       | description                                   |
+==============+===============================================+
| asav         | Cisco ASAv                                    |
| csr          | Cisco CSR 1000v                               |
| cumulus      | Cumulus VX 4.x or 5.x configured without NVUE |
| cumulus_nvue | Cumulus VX 5.x configured with NVUE           |
| dellos10     | Dell OS10                                     |
| eos          | Arista vEOS                                   |
| fortios      | Fortinet FortiOS firewall                     |
| frr          | FRR container                                 |
| iosv         | Cisco IOSv                                    |
| iosxr        | Cisco IOS XRv                                 |
| linux        | Generic Linux host                            |
| nxos         | Cisco Nexus 9300v                             |
| routeros     | Mikrotik RouterOS version 6                   |
| routeros7    | Mikrotik RouterOS version 7                   |
| srlinux      | Nokia SR Linux container                      |
| sros         | Nokia SR OS container                         |
| vmx          | Juniper vMX container                         |
| vsrx         | Juniper vSRX 3.0                              |
| vyos         | Vyatta VyOS VM/container                      |
+--------------+-----------------------------------------------+
```

* Displays Arista EOS information in YAML format:

```yaml
$ netlab show devices -d eos --format yaml
eos: Arista vEOS VM or cEOS container
```

## Display Device Images

```text
usage: netlab show images [-h] [--system] [--format {table,text,yaml}] [-d DEVICE]

Display default device images

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -d DEVICE, --device DEVICE
                        Display information for a single device
```

**Examples:**

* Display Vagrant boxes and container names for Arista EOS:

```text
$ netlab show images -d eos
eos image names by virtualization provider

+--------+-------------+-------------+--------------+
| device | libvirt     | virtualbox  | clab         |
+========+=============+=============+==============+
| eos    | arista/veos | arista/veos | ceos:4.26.4M |
+--------+-------------+-------------+--------------+
```

* Display Vagrant boxes and container names for Cumulus Linux in YAML format:

```yaml
$ netlab show images -d cumulus --format yaml
cumulus:
  clab: networkop/cx:4.4.0
  libvirt: CumulusCommunity/cumulus-vx:4.4.0
  virtualbox: CumulusCommunity/cumulus-vx:4.3.0
```

## Display Configuration Modules

```text
usage: netlab show modules [-h] [--system] [--format {table,text,yaml}] [-m MODULE]

Display supported configuration modules

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -m MODULE, --module MODULE
                        Display information for a single module
```

**Examples:** 

* Display configuration modules overview:

```text
$ netlab show modules
netlab Configuration modules and supported devices
===========================================================================
bfd:
  srlinux, sros, iosv, csr, nxos, eos, vyos, arubacx
bgp:
  cumulus, cumulus_nvue, eos, frr, csr, iosv, nxos, asav, vsrx, vyos,
  routeros, srlinux, sros, dellos10, routeros7, vmx, iosxr, arubacx,
  vptx
eigrp:
  csr, iosv, nxos
evpn:
  sros, srlinux, frr, eos, vyos, dellos10, cumulus, nxos, arubacx,
  vptx
gateway:
  eos, cumulus, iosv, csr, nxos, sros, srlinux, vyos, dellos10,
  arubacx
isis:
  eos, frr, csr, iosv, nxos, asav, vsrx, srlinux, sros, vyos, vmx,
  iosxr, vptx
mpls:
  eos, iosv, csr, routeros, vyos, routeros7, sros, vmx, vsrx, frr,
  vptx, arubacx
ospf:
  arcos, cumulus, cumulus_nvue, eos, fortios, frr, csr, iosv, nxos,
  vsrx, vyos, routeros, srlinux, sros, dellos10, routeros7, vmx,
  iosxr, arubacx, vptx
sr:
  csr, eos, srlinux, sros, vsrx, vmx, vptx
srv6:
  sros
vlan:
  eos, iosv, csr, vyos, dellos10, srlinux, routeros, nxos, frr,
  cumulus, sros, routeros7, vmx, vsrx, arubacx, vptx
vrf:
  eos, iosv, csr, routeros, dellos10, vyos, cumulus_nvue, nxos,
  srlinux, frr, cumulus, sros, routeros7, vmx, vsrx, arubacx, vptx
vxlan:
  eos, nxos, vyos, csr, dellos10, srlinux, frr, cumulus, sros,
  arubacx, vptx
```

* Display devices and features supported by BGP module:

```text
$ netlab show modules -m bgp
Devices and features supported by bgp module

+--------------+----------+--------------+---------------+-------------+----------+---------+
| device       | local_as | vrf_local_as | local_as_ibgp | activate_af | ipv6_lla | rfc8950 |
+==============+==========+==============+===============+=============+==========+=========+
| arubacx      |    x     |      x       |       x       |      x      |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| asav         |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| csr          |    x     |      x       |       x       |      x      |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| cumulus      |    x     |      x       |               |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| cumulus_nvue |          |              |               |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| dellos10     |    x     |      x       |               |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| eos          |    x     |      x       |       x       |      x      |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| frr          |    x     |      x       |               |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| iosv         |    x     |      x       |       x       |      x      |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| iosxr        |          |              |               |      x      |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| junos        |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| nxos         |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| routeros     |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| routeros7    |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| srlinux      |    x     |      x       |       x       |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| sros         |    x     |      x       |       x       |      x      |    x     |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| vmx          |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| vptx         |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| vsrx         |          |              |               |             |          |         |
+--------------+----------+--------------+---------------+-------------+----------+---------+
| vyos         |    x     |      x       |               |      x      |    x     |    x    |
+--------------+----------+--------------+---------------+-------------+----------+---------+

Notes:
* All devices listed in the table support bgp configuration module.
* Some devices might not support any module-specific additional feature

Feature legend:
* local_as: Supports local-as functionality
* vrf_local_as: Supports local-as within a VRF
* local_as_ibgp: Can use local-as to create IBGP sesssion
* activate_af: Can control activation of individual address families
* ipv6_lla: Can run EBGP sessions over IPv6 link-local addresses
* rfc8950: Can run IPv4 AF over IPv6 LLA EBGP session
```

* Display devices and features supported by EVPN module in YAML format:

```yaml
$ netlab show modules -m evpn --format yaml
arubacx:
  asymmetrical_irb: true
  irb: true
cumulus:
  asymmetrical_irb: true
  irb: true
dellos10:
  asymmetrical_irb: true
  irb: true
eos:
  asymmetrical_irb: true
  bundle:
  - vlan_aware
  irb: true
frr:
  irb: true
nxos:
  irb: true
srlinux:
  asymmetrical_irb: true
  irb: true
sros:
  asymmetrical_irb: true
  irb: true
vptx: {}
vyos:
  asymmetrical_irb: true
  irb: true
```

* Display device support for various initial configuration features:

```text
$ netlab show modules -m initial
Devices and features supported by initial module

+--------------+------------+-----------------+----------+
| device       | system_mtu | ipv4.unnumbered | ipv6.lla |
+==============+============+=================+==========+
| arubacx      |            |                 |          |
+--------------+------------+-----------------+----------+
| asav         |            |                 |          |
+--------------+------------+-----------------+----------+
| csr          |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| cumulus      |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| cumulus_nvue |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| dellos10     |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| eos          |     x      |        x        |    x     |
+--------------+------------+-----------------+----------+
| fortios      |            |                 |          |
+--------------+------------+-----------------+----------+
| frr          |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| iosv         |            |                 |    x     |
+--------------+------------+-----------------+----------+
| iosxr        |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| linux        |            |                 |          |
+--------------+------------+-----------------+----------+
| nxos         |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| routeros     |            |                 |          |
+--------------+------------+-----------------+----------+
| routeros7    |            |                 |          |
+--------------+------------+-----------------+----------+
| srlinux      |     x      |        x        |    x     |
+--------------+------------+-----------------+----------+
| sros         |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| vmx          |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| vptx         |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| vsrx         |            |        x        |    x     |
+--------------+------------+-----------------+----------+
| vyos         |            |        x        |    x     |
+--------------+------------+-----------------+----------+

Notes:
* All devices listed in the table support initial configuration module.
* Some devices might not support any module-specific additional feature

Feature legend:
* system_mtu: System-wide MTU setting
* ipv4.unnumbered: Unnumbered IPv4 interfaces
* ipv6.lla: IPv6 LLA-only interfaces
```

## Display Device Module Support

```text
usage: netlab show module-support [-h] [--system] [--format {table,text,yaml}]
                                  [-d DEVICE] [-m MODULE]

Display configuration modules supported by individual devices

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -d DEVICE, --device DEVICE
                        Display information for a single device
  -m MODULE, --module MODULE
                        Display information for a single module
```

**Examples:**

* Display configuration module support matrix:

```text
$ netlab show module-support
Configuration modules supported by individual devices

+--------------+-----+------+------+-------+-----+----+------+------+
| device       | bgp | isis | ospf | eigrp | bfd | sr | srv6 | evpn |
+==============+=====+======+======+=======+=====+====+======+======+
| arcos        |     |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| csr          | x   | x    | x    | x     | x   | x  |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| cumulus      | x   |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| cumulus_nvue | x   |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| eos          | x   | x    | x    |       | x   | x  |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| fortios      |     |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| frr          | x   | x    | x    |       |     |    |      | x    |
+--------------+-----+------+------+-------+-----+----+------+------+
| iosv         | x   | x    | x    | x     | x   |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| linux        |     |      |      |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| nxos         | x   | x    | x    | x     | x   |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| routeros     | x   |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| srlinux      | x   | x    | x    |       | x   | x  |      | x    |
+--------------+-----+------+------+-------+-----+----+------+------+
| sros         | x   | x    | x    |       | x   | x  | x    | x    |
+--------------+-----+------+------+-------+-----+----+------+------+
| vsrx         | x   | x    | x    |       |     | x  |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
| vyos         | x   |      | x    |       |     |    |      |      |
+--------------+-----+------+------+-------+-----+----+------+------+
```

* Display configuration modules available for Arista EOS:

```text
$ netlab show module-support -d eos
Configuration modules supported by eos

+--------+-----+------+------+-------+-----+----+------+------+
| device | bgp | isis | ospf | eigrp | bfd | sr | srv6 | evpn |
+========+=====+======+======+=======+=====+====+======+======+
| eos    | x   | x    | x    |       | x   | x  |      |      |
+--------+-----+------+------+-------+-----+----+------+------+
```

* Display EVPN module support:

```text
$ netlab show module-support -m evpn
evpn configuration module support

+--------------+------+
| device       | evpn |
+==============+======+
| arubacx      |  x   |
+--------------+------+
| asav         |      |
+--------------+------+
| csr          |      |
+--------------+------+
| cumulus      |  x   |
+--------------+------+
| cumulus_nvue |      |
+--------------+------+
| dellos10     |  x   |
+--------------+------+
| eos          |  x   |
+--------------+------+
| fortios      |      |
+--------------+------+
| frr          |  x   |
+--------------+------+
| iosv         |      |
+--------------+------+
| iosxr        |      |
+--------------+------+
| junos        |      |
+--------------+------+
| linux        |      |
+--------------+------+
| nxos         |  x   |
+--------------+------+
| routeros     |      |
+--------------+------+
| routeros7    |      |
+--------------+------+
| srlinux      |  x   |
+--------------+------+
| sros         |  x   |
+--------------+------+
| vmx          |      |
+--------------+------+
| vptx         |  x   |
+--------------+------+
| vsrx         |      |
+--------------+------+
| vyos         |  x   |
+--------------+------+
```

## Display Virtualization Providers

```text
$ netlab show providers -h
usage: netlab show providers [-h] [--system] [--format {table,text,yaml}] [-p PROVIDER]

Display supported virtualization providers

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -p PROVIDER, --provider PROVIDER
                        Display the status of the selected virtualization provider
```

**Examples:**

* Display a summary of virtualization providers and their state (executed on a Linux box with libvirt, KVM, vagrant, containerlab and Docker installed):

```text
$ netlab show providers
Supported virtualization providers

+------------+--------------------------+--------+
| provider   | description              | status |
+============+==========================+========+
| clab       | containerlab with Docker | OK     |
| external   | External devices         | OK     |
| libvirt    | Vagrant with libvirt/KVM | OK     |
| virtualbox | Vagrant with Virtualbox  | N/A    |
+------------+--------------------------+--------+
```

* Display the state of an installed provider (libvirt/KVM was installed on the host where the command was executed):

```text
$ netlab show providers -p libvirt
Status of libvirt (Vagrant with libvirt/KVM):

Executing: which kvm-ok
Executing: which virsh
Executing: which vagrant
Executing: ['bash', '-c', 'vagrant plugin list|grep vagrant-libvirt']
Executing: kvm-ok
Executing: virsh net-list

Status: OK
```

* Display the state of a failed/missing provider (Virtualbox was not installed on the host where the command was executed):

```text
$ netlab show providers -p virtualbox
Status of virtualbox (Vagrant with Virtualbox):

Executing: VBoxManage -h
Error executing VBoxManage -h:
  [Errno 2] No such file or directory: 'VBoxManage'

Status: N/A
```
