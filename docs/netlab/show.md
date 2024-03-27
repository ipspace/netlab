# Display System Information

**netlab show** command displays system settings in a tabular, text, or YAML format. The command can display system settings (as shipped with the *networklab* package) or system settings augmented with [user defaults](../defaults.md).

The following settings can be displayed:

* **[attributes](netlab-show-attributes)** -- Supported lab topology attributes
* **[defaults](netlab-show-defaults)** -- User/system [defaults](../defaults.md)
* **[devices](netlab-show-devices)** -- Supported devices
* **[images](netlab-show-images)** -- Vagrant box names or container names for all supported devices or a single device
* **[modules](netlab-show-modules)** -- Configuration modules
* **[module-support](netlab-show-module-support)** -- Configuration modules support matrix
* **[outputs](netlab-show-outputs)** -- Output modules used by the **[netlab create](create.md)** command
* **[reports](netlab-show-reports)** -- Report templates shipped with _netlab_
* **[providers](netlab-show-providers)** -- Virtualization providers

The system settings can be displayed as a table, as raw text that is easy to parse in automation scripts, and as YAML data that can be used by third-party utilities. See usage guidelines  and examples in individual command descriptions for more details.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(netlab-show-attributes)=
## Display Supported Lab Topology Attributes

The **netlab show attributes** command displays known lab topology attributes and their expected data types (please note that the optional `plugin` argument has to be the last argument in the command line):

```text
$ netlab show attributes -h
usage: netlab show attributes [-h] [--system] [--format {table,text,yaml}] [-m MODULE]
                              [--plugin PLUGIN [PLUGIN ...]]
                              [match]

Display supported global- or module-specific attributes

positional arguments:
  match                 Display a subset of attributes

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  -m MODULE, --module MODULE
                        Display information for a single module
  --plugin PLUGIN [PLUGIN ...]
                        Add plugin attributes to the system defaults
```

**Examples:**

* Display global VLAN attributes

```text
$ netlab show attributes vlan

You can use the following global vlan lab topology attributes:
=============================================================================

id:
  max_value: 4095
  min_value: 1
  type: int
mode:
  type: str
  valid_values:
  - bridge
  - irb
  - route
prefix: null
vni:
  max_value: 16777215
  min_value: 1
  type: int

=============================================================================
See https://netlab.tools/dev/validation/ for more data type- and
attribute validation details.
```

* Display SR-MPLS module attributes using YAML format to remove header and footer text

```yaml
$ netlab show attributes --module sr --format yaml
---
global:
  ipv6_sid_offset:
    min_value: 1
    type: int
  srgb_range_size:
    min_value: 1
    type: int
  srgb_range_start:
    min_value: 1
    type: int
node:
  ipv6_sid_offset:
    min_value: 1
    type: int
  srgb_range_size:
    min_value: 1
    type: int
  srgb_range_start:
    min_value: 1
    type: int
```

* Display BGP interface attributes

```yaml
$ netlab show attributes --module bgp interface --format yaml
---
local_as: asn
replace_global_as: bool
```

* Display BGP interface attributes when using **bgp.policy** plugin

```
$ netlab show attributes --module bgp --format yaml interface --plugin bgp.policy
---
local_as: asn
locpref:
  max_value: 4294967295
  min_value: 0
  type: int
med:
  max_value: 32767
  min_value: 0
  type: int
replace_global_as: bool
weight:
  max_value: 32767
  min_value: 0
  type: int
```

(netlab-show-defaults)=
## Display User/System Defaults

The **netlab show defaults** displays _netlab_ defaults collected from [user/system default files](../defaults.md):

```text
usage: netlab show defaults [-h] [--system] [--format {table,text,yaml}]
                            [--plugin PLUGIN [PLUGIN ...]]
                            [match]

Display (a subset) of system/user defaults

positional arguments:
  match                 Display defaults within the specified subtree

options:
  -h, --help            show this help message and exit
  --system              Display system information (without user defaults)
  --format {table,text,yaml}
                        Output format (table, text, yaml)
  --plugin PLUGIN [PLUGIN ...]
                        Add plugin attributes to the system defaults

```

**Notes**

* The `--plugin` argument must be the last parameter on the command line -- all tokens specified after it are added to the list of plugins
* The displayed information does not include lab-specific defaults specified in lab topology or [alternate default file locations](defaults-locations).
* You can also display system defaults with `netlab inspect defaults` (requires a running lab) or `netlab create -o yaml:defaults` (requires a working topology file)

**Examples**

Display [graph output module](../outputs/graph.md) defaults (**outputs.graph**):

```text
$ netlab show defaults outputs.graph

netlab default settings within the outputs.graph subtree
=============================================================================

as_clusters: true
colors:
  as: '#e8e8e8'
  ebgp: '#b21a1a'
  ibgp: '#613913'
  node: '#ff9f01'
  stub: '#d1bfab'
interface_labels: false
margins:
  as: 16
node_address_label: true
```

(netlab-show-devices)=
## Display Supported Devices

The **netlab show devices** command displays _netlab_-supported devices together with short descriptions.

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

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ device       ┃ description                                               ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ arubacx      │ ArubaOS-CX                                                │
│ asav         │ Cisco ASAv                                                │
│ csr          │ Cisco CSR 1000v                                           │
│ cumulus      │ Cumulus VX 4.x or 5.x configured without NVUE             │
│ cumulus_nvue │ Cumulus VX 5.x configured with NVUE                       │
│ dellos10     │ Dell OS10                                                 │
│ eos          │ Arista vEOS VM or cEOS container                          │
│ fortios      │ Fortinet FortiOS firewall                                 │
│ frr          │ FRR container                                             │
│ iosv         │ Cisco IOSv                                                │
│ iosxr        │ Cisco IOS XRv                                             │
│ junos        │ Generic Juniper device (meta device, used only as parent) │
│ linux        │ Generic Linux host                                        │
│ nxos         │ Cisco Nexus 9300v                                         │
│ routeros     │ Mikrotik RouterOS version 6                               │
│ routeros7    │ Mikrotik RouterOS version 7                               │
│ srlinux      │ Nokia SR Linux container                                  │
│ sros         │ Nokia SR OS container                                     │
│ vmx          │ Juniper vMX container                                     │
│ vptx         │ Juniper vPTX                                              │
│ vsrx         │ Juniper vSRX 3.0                                          │
│ vyos         │ Vyatta VyOS VM/container                                  │
└──────────────┴───────────────────────────────────────────────────────────┘

Networking daemons supported by netlab

┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ daemon ┃ description                  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ bird   │ BIRD Internet Routing Daemon │
└────────┴──────────────────────────────┘
```

* Displays Arista EOS information in YAML format:

```yaml
$ netlab show devices -d eos --format yaml
eos: Arista vEOS VM or cEOS container
```

* Displays BIRD information in YAML format:

```yaml
$ netlab show devices -d bird --format yaml
bird:
  daemon: true
  description: BIRD Internet Routing Daemon
  parent: linux
```

(netlab-show-images)=
## Display Device Images

The **netlab show images** command displays built-in box/container names for supported network devices. If you want to use different Vagrant box names or container names, change them in [user defaults](../defaults.md) or in [lab topology](node-attributes).

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
| eos    | arista/veos | arista/veos | ceos:4.31.2F |
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

(netlab-show-modules)=
## Display Configuration Modules

The **netlab show modules** command displays available configuration modules and devices supported by each configuration module. When displaying a single module, the command lists optional features supported by that module and the devices implementing them.

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

* When using the `initial` pseudo-module, the command displays device support for various initial configuration features:

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

(netlab-show-module-support)=
## Display Device Module Support

The **netlab show module-support** command displays configuration modules supported by individual devices.

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

(netlab-show-outputs)=
## Display Output Modules

The **netlab show outputs** command displays [output formats](../outputs/index.md) supported by the **[netlab create](create.md)** command.

```text
usage: netlab show outputs [-h] [--system] [--format {table,text,yaml}]

Display output modules for the "netlab create" command

options:
  -h, --help            show this help message and exit
  --format {table,text,yaml}
                        Output format (table, text, yaml)
```

Example: display output modules as a table

```text
$ netlab show outputs
Supported output modules

+----------+--------------------------------------------------------+
| module   | description                                            |
+==========+========================================================+
| ansible  | Ansible inventory and configuration file               |
| d2       | Topology graph in D2 format                            |
| devices  | Create simple device inventory as a YAML file          |
| graph    | Topology graph in graphviz format                      |
| json     | Inspect transformed data in JSON format                |
| provider | Create virtualization provider configuration file(s)   |
| report   | Create a report from the transformed lab topology data |
| tools    | Create configuration files for external tools          |
| yaml     | Inspect transformed data in YAML format                |
+----------+--------------------------------------------------------+
```

(netlab-show-reports)=
## Display Report Templates

The **netlab show reports** command displays the report templates that can be used with the **[netlab report](report.md)** command.

```text
usage: netlab show reports [-h] [--format {table,text,yaml}] [match]

Display available system reports

positional arguments:
  match                 Display report names containing the specified string

options:
  -h, --help            show this help message and exit
  --format {table,text,yaml}
                        Output format (table, text, yaml)
```

**Examples**

* Display all available report templates[^R162]

[^R162]: Printout produced with _netlab_ release 1.6.2. The list of reports might be longer by now.

```text
$ netlab show reports

HTML reports

+----------------------+--------------------------------------------+
| report               | description                                |
+======================+============================================+
| addressing-link.html | Link/interface addressing                  |
| addressing-node.html | Node/interface addressing                  |
| addressing.html      | Node/interface and link addressing         |
| bgp-asn.html         | BGP autonomous systems (needs Ansible)     |
| bgp-neighbor.html    | BGP neighbors                              |
| bgp.html             | BGP autonomous systems and neighbors       |
| mgmt.html            | Device management interfaces and addresses |
| wiring.html          | Lab wiring (used with external provider)   |
+----------------------+--------------------------------------------+

text reports

+------------+------------------------------------------------------+
| report     | description                                          |
+============+======================================================+
| addressing | Node/interface addressing                            |
| bgp        | BGP autonomous systems and neighbors (needs Ansible) |
| mgmt       | Device management interfaces and addresses           |
| wiring     | Lab wiring (used with external provider)             |
+------------+------------------------------------------------------+

Markdown reports

+-----------------+----------------------------------------+
| report          | description                            |
+=================+========================================+
| addressing.md   | Node/interface addressing              |
| bgp-asn.md      | BGP autonomous systems (needs Ansible) |
| bgp-neighbor.md | BGP neighbors                          |
| wiring.md       | Lab wiring                             |
+-----------------+----------------------------------------+
```

* Display BGP reports

```
$ netlab show reports bgp
+--------+-------------------+------------------------------------------------------+
| format | report            | description                                          |
+========+===================+======================================================+
| html   | bgp-asn.html      | BGP autonomous systems (needs Ansible)               |
|        | bgp-neighbor.html | BGP neighbors                                        |
|        | bgp.html          | BGP autonomous systems and neighbors                 |
| md     | bgp-asn.md        | BGP autonomous systems (needs Ansible)               |
|        | bgp-neighbor.md   | BGP neighbors                                        |
| text   | bgp               | BGP autonomous systems and neighbors (needs Ansible) |
+--------+-------------------+------------------------------------------------------+
```
(netlab-show-providers)=
## Display Virtualization Providers

The **netlab show providers** command displays supported virtualization providers and their status:

* OK: the provider is installed and operational
* FAIL: the provider is installed, but not working correcty
* N/A: the provider is probably not installed

Use the `-p` option to display commands used to probe the operational state of an individual provider, and their results.

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
