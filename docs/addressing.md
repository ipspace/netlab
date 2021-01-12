# Topology Address Pools

The initial release of **create-topology** tool used simple address configuration described at the bottom of this document. Release 0.2 introduced structured address pools.

## Address Pools Overview

**create-topology** tool uses multiple address pools to create automatic address plans for the desired lab topology:

* **mgmt** pool: Management IPv4 and MAC addresses. IPv6 addresses are assigned if specified, but not used at the moment.
* **loopback** pool: Loopback IPv4 and IPv6 addresses.
* **lan** pool: IPv4 and IPv6 addresses used on multi-access segments (connecting more than two nodes or having **type** set to *lan*)
* **p2p** pool (optional): IPv4 and IPv6 addresses used on point-to-point links
* **stub** pool (optional): IPv4 and IPv6 addresses used on stub links (links connected to a single network device). This pool is not used in release 0.2

You can specify additional address pools, but they are not used in release 0.2. A future release will add support for custom address pools.

## Dual-Stack Support

Every address pool could have an IPv4 and an IPv6 prefix, supporting IPv4-only, dual-stack or IPv6-only deployments. Pool address space is specified in **ipv4** or **ipv6** CIDR prefix. Size of individual IPv4 address allocations is specified with the **prefix** parameter, IPv6 prefixes are currently fixed  (/64).

## Specifying Address Pools

Address pools could be specified:

* In **addressing** or **defaults.addressing** part of topology YAML file
* In **addressing** part of local or global defaults file.

**Notes:**
* Local defaults file is specified with `--defaults` CLI option (default value: `topology-defaults.yml` in current directory)
* Global defaults file is `topology-defaults.yml` in script directory.

Each address pool specification is a dictionary of address pools. Individual address pools are specified with these parameters:

* **ipv4** - IPv4 CIDR prefix
* **ipv6** - IPv6 CIDR prefix
* **prefix** - IPv4 subnet allocation size (IPv6 subnets use /64 prefixes)
* **start** - first subnet or first IP address offset. Used primarily with **loopback** pool to ensure the first devices gets x.x.x.1/32 IP address, and with **mgmt** pool to specify the first management IP address).

**Notes:**

* Default IPv4 subnet allocation size is 32 for `loopback` pool, 24 for `lan` pool and 30 for `p2p` pool. All other pools must specify the **prefix** parameter whenever the **ipv4** parameter is specified.
* IPv4 loopback pool starts at .1 (**start** parameter is assumed to be 1)
* IPv6 loopback pool starts at the second subnet to make loopback IPv6 address similar to its IPv4 counterpart.

### Example

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

## Merging Defaults

Numerous default address pool configurations are merged during the topology processing:

* Local defaults and global defaults are deep-merged with **defaults** dictionary in topology file
* **defaults.addressing** topology section is deep-merged with **addressing** topology section
* Legacy parameters (release 0.1 syntax) from the **defaults** topology section are deep-merged with the **addressing** section (making them least-preferred).

**Notes on deep merging:**

The **create-topology** tool performs recursive merge of configuration dictionaries:

* Dictionary keys not present in target dictionary are added from the defaults dictionary;
* Whenever a key in the target dictionary is itself a dictionary, and the same key is present in the defaults dictionary, the merge process recurses, resulting in a recursive merge of child dictionaries.
* Lists and scalar values are not merged.

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

## Legacy Addressing Configuration (Release 0.1)

Release 0.1 used individual parameters in **defaults** section (specified in topology file, local defaults, or global defaults) to specify address pools:

* **lan**: IPv4 CIDR prefix for multi-access links
* **lan_subnet**: Prefix size for subnets in *lan* pool
* **loopback**: Python format string that results in IPv4 CIDR prefix used on loopback interfaces
* **mgmt_ip**: Python format string that results in IPv4 addresses used on management interfaces
* **mgmt_mac**: Python format string that results in MAC addresses used on management interfaces
* **p2p**: IPv4 CIDR prefix for P2P links
* **p2p_subnet**: Prefix size for subnets in *p2p* pool

These parameters SHOULD NOT be used in release 0.2. When they're present in **defaults** section or a defaults file they're merged with the corresponding **addressing** parameters.
