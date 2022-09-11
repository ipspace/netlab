# VLAN integration test cases

This directory contains numerous topologies you can use to test your VLAN implementation. Many topologies use Linux hosts as attached devices, making it possible to run them under most virtualization providers supported by *netlab*.

The virtualization provider and the device under test are not specified in the topology. Start the lab with

```
netlab up -p <provider> -d <device> <topology-file>
```

The topologies (in increasing order of complexity) implement the following scenarios:

### Single node bridging

* `vlan-bridge-single.yml` -- single VLAN bridged between two ports
* `vlan-bridge-multiple.yml` -- two 2-port access VLANs

### Single node bridging + routing (IRB) on the same VLAN

* `vlan-irb-single.yml` -- single IRB VLAN
* `vlan-irb-multiple.yml` -- two IRB VLANs
* `vlan-mixed-multiple.yml` -- a mix of bridging-only and IRB VLANs

### VLAN trunks

* `vlan-bridge-trunk.yml` -- a trunk with two bridged VLANs
* `vlan-bridge-trunk-router.yml` -- a trunk with two bridge VLANs and an external router attached to one of the switches
* `vlan-irb-trunk.yml` -- a trunk with two L2/L3 (IRB) VLANs

### Routed VLAN subinterfaces

* `vlan-routed-trunk.yml` -- a router-on-a-stick is attached to a VLAN trunk. Make sure the router configuration uses routed subinterfaces and not VLAN interfaces.
* `vlan-vrf-lite.yml` -- implement VRF lite across three routers using VLAN trunks

### Consolidated VLAN test cases

* `vlan-all-in-one.yml` -- contains all variations of access and trunk vlans in various supported modes, with/without native vlan. Used to test config generation
