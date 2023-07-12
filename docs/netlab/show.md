# Display System Information

**netlab show** displays system settings in a tabular form. The following settings can be displayed:

* **devices** -- Valid device types
* **images** -- Vagrant box names or container names for all supported devices or a single device
* **module** -- Configuration modules
* **module-support** -- Configuration modules support matrix

## Usage

```text
usage: netlab show [-h] [-d DEVICE] [-m MODULE] [--system]
                   [--format {table,text,yaml}]
                   {images,devices,module-support,modules}

Display default settings

positional arguments:
  {images,devices,module-support,modules}
                        Select the system information to display

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Display information for a single device
  -m MODULE, --module MODULE
                        Display information for a single module
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
```

## Examples

Valid devices:

```
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

Vagrant boxes and container names for Arista EOS:

```
$ netlab show images -d eos
eos image names by virtualization provider

+--------+-------------+-------------+--------------+
| device | libvirt     | virtualbox  | clab         |
+========+=============+=============+==============+
| eos    | arista/veos | arista/veos | ceos:4.26.4M |
+--------+-------------+-------------+--------------+
```

Configuration modules overview:

```
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

Configuration modules available for Arista EOS:

```
$ netlab show module-support -d eos
Configuration modules supported by eos

+--------+-----+------+------+-------+-----+----+------+------+
| device | bgp | isis | ospf | eigrp | bfd | sr | srv6 | evpn |
+========+=====+======+======+=======+=====+====+======+======+
| eos    | x   | x    | x    |       | x   | x  |      |      |
+--------+-----+------+------+-------+-----+----+------+------+
```

Configuration module support matrix:

```
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

EVPN features supported by individual devices:

```text
$ netlab show modules -m evpn
Devices and features supported by evpn module

+----------+-----+------------------+------------+
| device   | irb | asymmetrical_irb | bundle     |
+==========+=====+==================+============+
| sros     |  x  |        x         |            |
+----------+-----+------------------+------------+
| srlinux  |  x  |        x         |            |
+----------+-----+------------------+------------+
| frr      |  x  |                  |            |
+----------+-----+------------------+------------+
| eos      |  x  |        x         | vlan_aware |
+----------+-----+------------------+------------+
| vyos     |  x  |        x         |            |
+----------+-----+------------------+------------+
| dellos10 |  x  |        x         |            |
+----------+-----+------------------+------------+
| cumulus  |  x  |        x         |            |
+----------+-----+------------------+------------+
| nxos     |  x  |                  |            |
+----------+-----+------------------+------------+
| arubacx  |  x  |        x         |            |
+----------+-----+------------------+------------+
| vptx     |     |                  |            |
+----------+-----+------------------+------------+

Notes:
* All devices listed in the table support evpn configuration module.
* Some devices might not support any module-specific additional feature

Feature legend:
* irb: Supports symmetrical IRB (routing on ingress and egress)
* asymmetrical_irb: Support asymmetrical IRB (routing on ingress, bridging on egress)
* bundle: EVPN bundle service support
```

Device support for various initial configuration features:

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