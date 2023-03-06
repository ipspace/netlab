# Display System Information

**netlab show** displays system settings in a tabular form. The following settings can be displayed:

* **devices** -- Valid device types
* **images** -- Vagrant box names or container names for all supported devices or a single device
* **module-support** -- Configuration modules support matrix

## Usage

```
usage: netlab show [-h] [-d DEVICE] [--system] {images,devices,module-support}

Display default settings

positional arguments:
  {images,devices,module-support}
                        Select the system information to display

options:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Display information for a single device
  --system              Display system information (without user defaults)
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
