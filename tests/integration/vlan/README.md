# VLAN integration test cases

This directory contains numerous topologies you can use to test your VLAN implementation.
Many topologies use Linux hosts as attached devices, making it possible to run them under
most virtualization providers supported by *netlab*.

The virtualization provider and the device under test are not specified in the topology.
Start the lab with

```
netlab up -p <provider> -d <device> <topology-file>
```

After validating the basic setup (single-node bridging and VLAN trunks), you might want
to make one of the switches a third-party switch (example: Cumulus Linux) to validate
cross-platform interoperability. Use a command similar to:

```
netlab up -p <provider> -d <device> -s nodes.s1.device=cumulus <topology-file>
```

Finally, you might want to use third-party devices as layer-2 switches in the _routed
subinterfaces_ scenarios if you're working with a platform that is a resource hog or
uses a long time to start. Use something like:

```
netlab up -p <provider> -d cumulus -s nodes.s1.ros=<device> <topology-file>
```

Topologies using Linux hosts have validation tests. Execute them with **netlab validate**.

The topologies (in increasing order of complexity) implement the following scenarios:

### Single node bridging

* `vlan-bridge-single.yml` -- single VLAN bridged between two ports
* `vlan-bridge-multiple.yml` -- two 2-port access VLANs

### Single node bridging + routing (IRB) on the same VLAN

* `vlan-irb-single.yml` -- single IRB VLAN
* `vlan-irb-multiple.yml` -- two IRB VLANs
* `vlan-mixed-multiple.yml` -- tests a combination of bridged and IRB VLANs on a single node

### VLAN trunks

* `vlan-bridge-trunk.yml` -- a trunk with two bridged VLANs
* `vlan-bridge-trunk-router.yml` -- a trunk with two bridge VLANs and an external
  router attached to one of the switches. The router has two interfaces, not a VLAN trunk.
  This scenario checks that the bridged VLANs don't handle IP traffic.
* `vlan-irb-trunk.yml` -- a trunk with two L2/L3 (IRB) VLANs

### Native VLANs on VLAN trunks

* `vlan-bridge-native.yml` -- a trunk with two bridged VLANs, one of them configured as
  native VLAN on the trunk
* `vlan-irb-native.yml` -- a trunk with two VLANs in IRB mode (each switch has a L3
  interface), one of them configured as native VLAN on the trunk

### Routed VLAN subinterfaces

* `vlan-routed-trunk.yml` -- a router-on-a-stick is attached to a VLAN trunk. Make sure the
  router configuration uses routed subinterfaces and not VLAN interfaces.
* `vlan-vrf-lite.yml` -- implement VRF lite across three routers using VLAN trunks

### Weird scenarios

* `vlan-routed-native.yml` -- a router-on-a-stick is attached to a VLAN trunk, one of the
  routed VLANs is a native VLAN. This configuration should be handled by most L3 switches
  and routers
* `vlan-mixed-trunk.yml` -- a combination of bridged and routed VLANs on the same set
  of ports. Most layer-3 switches cannot handle this combination.
* `vlan-mixed-native.yml` -- Similar to `vlan-mixed-trunk.yml`, but the routed trunk
  is a native VLAN. Few devices can handle this combination.

### Consolidated VLAN test cases

* `vlan-vrf-route-leaking.yml` -- implement VRF lite with inter-VRF EBGP session
* `vlan-all-in-one.yml` -- contains all variations of access and trunk vlans in various supported modes, with/without native vlan. Used to test config generation
