# Addressing Tutorial

IP Address Management (IPAM) is one of the most interesting *netlab* features -- it allows you to create full-blown fully configured networking labs without spending a millisecond  on IP addressing scheme, assigning IP addresses to nodes and interfaces, or configuring them on network devices.

This document starts with an easy walk through simple addressing schemes, gets progressively more complex, and ends with crazy scenarios like stretched subnets (eventually, we're not there yet).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Basics

*netlab* uses a two-step IP address allocation during the [lab topology transformation process](../dev/transform.md):

* A prefix is assigned to every link in the lab topology
* An IPv4/IPv6 address is assigned to every node attached to a link

Of course it's a bit more complex than that:

* A link prefix could could contain an IPv4 subnet, an IPv6 subnet, or both.
* You can assign a static **prefix** to a link or let *netlab* get one from an address pool.
* You can assign static IPv4 and/or IPv6 addresses to every interface connected to a link, or remove an address from a particular interface.
* *netlab* also supports unnumbered IPv4 interface, LLA-only IPv6 interfaces, and links/interfaces without IPv4/IPv6 addresses (in case you want to test layer-2 functionality).

Don't get scared by the plethora of options -- getting started with built-in address pools is as easy as it can get.

```{include} addr-builtin.txt
```
```{include} addr-custom-pools.txt
```
```{include} addr-static.txt
```
```{include} addr-ipv6.txt
```
```{include} addr-complex.txt
```
