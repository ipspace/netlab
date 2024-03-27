# VXLAN integration test cases

This directory contains numerous topologies you can use to test your VXLAN implementation. Many topologies use Linux hosts as attached devices, making it possible to run them under most virtualization providers supported by *netlab*.

The virtualization provider and the device under test are not specified in the topology. Start the lab with

```
netlab up -p <provider> -d <device> <topology-file>
```

After validating the VXLAN functionality, you might want
to make one of the switches a third-party switch (for example, Cumulus Linux) to validate cross-platform interoperability. Use a command similar to:

```
netlab up -p <provider> -d <device> -s nodes.s1.device=cumulus <topology-file>
```

Topologies using Linux hosts have validation tests. Execute them with **netlab validate**.

The topologies (in increasing order of complexity) implement the following scenarios:

### VXLAN Bridging

* `vxlan-bridging.yml` -- two VXLAN segments spanning three switches
* `vxlan-alt-vtep.yml` -- VXLAN bridging with non-default VTEP IP addresses
* `vxlan-bridging-multivendor.yml` -- a multi-vendor bridging lab. One of the devices is a Cumulus Linux switch.
* `vxlan-bridging-v6only.yml` -- VXLAN bridging between IPv6 VTEPs

### Asymmetrical IRB

* `vlan-irb.yml` -- simple two-segment IRB test case. Switches have VLAN interfaces with IP addresses.
* `vlan-irb-ospf.yml` -- IRB test case with OSPF running in the VXLAN segments.

### VXLAN-to-VXLAN Routing

* `vxlan-router-stick.yml` -- router-on-a-stick performing VXLAN-to-VXLAN routing.
