# Display System Information

**netlab show** displays system settings in a tabular form. The following settings can be displayed:

* **images** -- Vagrant box names or container names for all supported devices or a single device
* **module-support** -- Configuration modules support matrix

## Usage

```
usage: netlab show [-h] [-d DEVICE] {images,module-support}

Display system settings

positional arguments:
  {images,module-support}
                        Select the system information to display

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Display system information for a single device
```

## Examples

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
