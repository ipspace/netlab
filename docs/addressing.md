# Topology Address Pools

Lab topology transformation code assigns IPv4 and IPv6 subnets (prefixes) to individual links and loopback interfaces from *address pools*. Node addresses are then assigned from the prefixes assigned to individual links.

```{tip}
You can assign a static prefix to a link with **prefix** link attribute and static IP address to an interface with an **ipv4** or **ipv6** attribute of node-on-link data. For more details, see [static link addressing](links.md#static-link-addressing).
```

*netlab* use multiple predefined address pools:

* **mgmt** pool: Management IPv4 and MAC addresses. IPv6 addresses are assigned if specified, but not used at the moment.
* **loopback** pool: Loopback IPv4 and IPv6 addresses.
* **lan** pool: IPv4 and IPv6 addresses used all links apart from P2P links (links with more or less than two nodes attached to them), or links with **type** set to *lan*.
* **p2p** pool: IPv4 and IPv6 addresses used on point-to-point links
* **router_id** pool is used to allocate BGP router IDs in IPv6-only networks.
* **l2only** pool has no IPv4 or IPv6 addresses. You can use it to create L2-only links. See [layer-2-only pools](#layer-2-only-pools) and *[Using l2only Address Pool](example/addressing-tutorial.md#layer-2-only-links-using-l2only-address-pool)* for details.
* **vrf_loopback** pool: IPv4 and IPv6 prefixes used on optional VRF loopback interfaces.

You can specify additional address pools, and [use them with the **pool** link attribute](links.md#selecting-custom-address-pools).

Default IPv4 address pools are defined in system settings:

```
addressing:
  loopback:
    ipv4: 10.0.0.0/24
  router_id:
    ipv4: 10.0.0.0/24
    prefix: 32
  lan:
    ipv4: 172.16.0.0/16
  p2p:
    ipv4: 10.1.0.0/16
  mgmt:
    ipv4: 192.168.121.0/24
    start: 100
    mac: 08-4F-A9-00-00-00
  l2only:
  vrf_loopback:
    ipv4: 10.2.0.0/24
    prefix: 32
```

You can override or augment them in topology **addressing** element. You can also override individual **defaults.addressing** components.

## Dual-Stack Support

Every address pool could have an IPv4 and an IPv6 prefix, supporting IPv4-only, dual-stack or IPv6-only deployments. Pool address space is specified in **ipv4** or **ipv6** CIDR prefix. Size of individual IPv4 address allocations is specified with the **prefix** parameter, IPv6 prefixes are currently fixed  (/64).

## Specifying Address Pools

Address pools could be specified:

* In **addressing** or **defaults.addressing** part of topology YAML file
* In **addressing** part of local or global defaults file.

```{tip}
* [Local (or user) defaults file](defaults-user-file) can be overwritten with `--defaults` option of **netlab create** or **netlab up** command.
* Global defaults file is `topology-defaults.yml` included in *netlab* package.
```

Each address pool specification is a dictionary of address pools. Individual address pools are specified with these parameters:

* **ipv4** -- IPv4 CIDR prefix or **true** for unnumbered IPv4 links
* **ipv6** -- IPv6 CIDR prefix or **true** for LLA-only IPv6 links.
* **unnumbered** -- unnumbered address pool. Interfaces attached to nodes based on this address pool will have IPv4 and/or IPv6 enabled based on the protocols enabled on node's loopback interface.
* **prefix** - IPv4 subnet allocation size. IPv6 subnets use /64 prefixes that cannot be changed.
* **start** - first subnet or first IP address offset. Used primarily with **loopback** pool to ensure the first devices gets x.x.x.1/32 IP address, and with **mgmt** pool to specify the first management IP address.

**Notes:**

* Default IPv4 subnet allocation size is 32 for `loopback` pool, 24 for `lan` pool and 30 for `p2p` pool. All other pools must specify the **prefix** parameter whenever the **ipv4** parameter is specified.
* IPv4 loopback pool starts at .1 (**start** parameter is assumed to be 1)
* IPv6 loopback pool starts at the second subnet to make loopback IPv6 address similar to its IPv4 counterpart.

### Address Pool Configuration Example

This is the default addressing configuration from global `topology-defaults.yml`:

```
addressing:
  loopback:
    ipv4: 10.0.0.0/24
  lan:
    ipv4: 172.16.0.0/16
  p2p:
    ipv4: 10.1.0.0/16
  mgmt:
    ipv4: 192.168.121.0/24
    start: 100
    mac: 08-4F-A9-00-00-00
```

* It specifies IPv4-only addressing scheme
* Loopback IP addresses are assigned from 10.0.0.0/24 CIDR block. The first assigned address is 10.0.0.1/32 (see *notes* above for details).
* LAN IP addresses are assigned from 172.16.0.0/16 CIDR block. Subnet prefix is /24 (see *notes* above for details).
* P2P IP addresses are /30 subnets from 10.1.0.0/16 CIDR block.
* Management IP addresses are assigned from 192.168.121.0/24 CIDR block. The first IP address is 192.168.121.101 (*start* offset plus node ID)
* MAC addresses of management interfaces start with 08-4F-A9. The last byte of the MAC address is the node ID.

(addressing-unnumbered)=
## Unnumbered Interface Support

*netlab* supports unnumbered IPv4 and IPv6 interfaces: 

* Unnumbered IPv4 interfaces are not supported on all platforms and use *loopback* address as the proxy address of the unnumbered interface.
* Unnumbered IPv6 interfaces use only LLA IPv6 address -- IPv6 is enabled on an interface, but no static IPv6 address is assigned to it.

You can create unnumbered interfaces in two ways:

* Create a custom pool with no **ipv4** or **ipv6** attribute and set **unnumbered** attribute **true**. Interfaces using this address pool will get IPv4 and/or IPv6 enabled based on protocols enabled on the loopback interface.
* Use **ipv4: true** or **ipv6: true** instead of specifying an IPv4 or IPv6 prefix for the address pool. See *[Specifying Address Pools](#specifying-address-pools)* section for details.

For more details, see *[Unnumbered Interface Example](#unnumbered-interface-example)* below.

## Layer-2-only Pools

An address pool with no attributes is a layer-2-only pool. Links using such a pool have no IPv4/IPv6 prefix, and interfaces attached to such links get no IPv4/IPv6 address assigned from the on-link prefix.

*netlab* has predefined **l2only** pool that you can use to create layer-2-only links, for example: 

```
# CLNS lab
#
nodes: [ r1, r2, r3 ]

links:
- r1:
  r2:
  r3:
  pool: l2only
```

## Merging Defaults

Numerous default address pool configurations are merged during the topology processing:

* Local defaults and global defaults are deep-merged with **defaults** dictionary in topology file
* **defaults.addressing** topology section is deep-merged with **addressing** topology section
* Legacy parameters (release 0.1 syntax) from the **defaults** topology section are deep-merged with the **addressing** section (making them least-preferred).

For more information on *deep merging*, please read the [topology defaults](defaults.md) document.

### Example

The following address configuration in lab topology file...

```
addressing:
  loopback:
    ipv6: 2001:db8:0::/48
  lan:
    ipv4: 10.2.0.0/16
    ipv6: 2001:db8:1::/48
    prefix: 26
```

... results in the following address pools when combined with the global defaults (see above):

```
lan:
  ipv4: 10.2.0.0/16
  ipv6: 2001:db8:1::/48
  prefix: 26
loopback:
  ipv4: 10.0.0.0/24
  ipv6: 2001:db8:0::/48
  prefix: 32
mgmt:
  ipv4: 192.168.121.0/24
  mac: 08-4F-A9-00-00-00
  start: 100
p2p:
  ipv4: 10.1.0.0/16
  prefix: 30
```

## Unnumbered Interface Example

The following topology file creates a LAN and an unnumbered P2P link between a pair of Cisco CSR1000v routers:

```
addressing:
  core:
    unnumbered: true

defaults:
  device: csr

nodes:
- r1
- r2

links:
- name: Unnumbered link between R1 and R2
  r1:
  r2:
  pool: core

- name: LAN link between R1 and R2
  r1:
  r2:
  type: lan
```

The topology results in the following Ansible inventory data for R1 (please note **ipv4: true** attribute and lack of IPv4/IPv6 addresses on the first link).

```
---
box: cisco/csr1000v
links:
- ifindex: 2
  ifname: GigabitEthernet2
  ipv4: true
  linkindex: 1
  name: Unnumbered link between R1 and R2
  neighbors:
    r2:
      ifname: GigabitEthernet2
      ipv4: true
  pool: core
  remote_id: 2
  remote_ifindex: 2
  type: p2p
  unnumbered: true
- bridge: X_2
  ifindex: 3
  ifname: GigabitEthernet3
  ipv4: 172.16.0.1/24
  linkindex: 2
  name: LAN link between R1 and R2
  neighbors:
    r2:
      ifname: GigabitEthernet3
      ipv4: 172.16.0.2/24
  type: lan
loopback:
  ipv4: 10.0.0.1/32
mgmt:
  ifname: GigabitEthernet1
  ipv4: 192.168.121.101
  mac: 08-4F-A9-00-00-01
```
