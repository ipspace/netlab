# VRF integration test cases

This directory contains numerous topologies you can use to test your VRF implementation. Many topologies use Linux hosts as attached devices, making it possible to run them under most virtualization providers supported by *netlab*.

The topology does not specify the virtualization provider and the device under test. The easiest way to specify them is to use environment variables:

```
$ export NETLAB_DEVICE=<device-type>
$ export NETLAB_PROVIDER=<provider-type>
```

The topologies (in increasing order of complexity) implement the following scenarios:

## VRF Lite with hosts

* `01-multi-vrf.yml` -- two isolated VRFs on a single device
* `02-multi-vrf-ipv6.yml` -- two isolated IPv6-only VRFs on a single device
* `03-multi-vrf-loopback.yml` -- two isolated VRFs with loopbacks on a single device
* `04-multi-vrf-loopback-ipv6.yml` -- two isolated IPv6-only VRFs with loopbacks on a single device

## VRF Lite with OSPF routers

* `11-multi-vrf-ospf.yml` -- two isolated VRFs with OSPF routers attached to device under test
* `15-multi-vrf-mixed.yml` -- similar to other multi-VRF test cases, but using a combination of OSPF and BGP in every VRF
* `21-multi-vrf-ospfv3.yml` -- two isolated IPv6-only VRFs with OSPFv3 routers attached to device under test

## VRF Lite with BGP routers

* `12-multi-vrf-bgp.yml` -- two isolated VRFs with BGP CE-routers attached to device under test
* `13-multi-vrf-bgp-loopback.yml` -- two isolated VRFs with VRF loopbacks on the PE-router and BGP as PE-CE routing protocol
* `14-multi-vrf-unnumbered-bgp.yml` -- Similar to `12-multi-vrf-bgp`, but using interface EBGP sessions.
* `15-multi-vrf-mixed.yml` -- similar to other multi-VRF test cases, but using a combination of OSPF and BGP in every VRF
* `22-multi-vrf-bgp-ipv6.yml` -- two isolated IPv6-only VRFs with BGP CE-routers attached to the device under test

### VRF loopbacks

* `03-multi-vrf-loopback.yml` -- two isolated VRFs with loopbacks on a single device
* `04-multi-vrf-loopback-ipv6.yml` -- two isolated IPv6-only VRFs with loopbacks on a single device
* `13-multi-vrf-bgp-loopback.yml` -- two isolated VRFs with VRF loopbacks on the PE-router and BGP as PE-CE routing protocol

### Inter-VRF Route Leaking

* `31-vrf-common-hosts.yml` -- common services VRF on a single device
* `32-vrf-common-hosts-ipv6.yml` -- common services IPv6-only VRF on a single device
* `33-vrf-common-ospf.yml` -- common services VRF with OSPF routers attached to all VRFs
* `23-vrf-common-mixed.yml` -- common services VRF with OSPF in spoke VRFs and BGP in common VRF
