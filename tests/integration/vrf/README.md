# VRF integration test cases

This directory contains numerous topologies you can use to test your VRF implementation. Many topologies use Linux hosts as attached devices, making it possible to run them under most virtualization providers supported by *netlab*.

The virtualization provider and the device under test are not specified in the topology. Start the lab with

```
netlab up -p <provider> -d <device> <topology-file>
```

The topologies (in increasing order of complexity) implement the following scenarios:

### VRF Lite with hosts

* `multi-vrf.yml` -- two isolated VRFs on a single device
* `vrf-route-leaking.yml` -- common services VRF on a single device

### VRF Lite with OSPF routers

* `multi-vrf-ospf.yml` -- two isolated VRFs with OSPF routers attached to device under test
* `vrf-common-ospf.yml` -- common services VRF with OSPF routers attached to all VRFs

### VRF Lite with BGP routers

* `multi-vrf-bgp.yml` -- two isolated VRFs with BGP CE-routers attached to device under test
* `multi-vrf-mixed.yml` -- similar to other multi-vrf test cases, but using combination of OSPF and BGP in every VRF
