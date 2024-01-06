# Initial configuration integration test cases

This directory contains topologies you can use to test your initial device configuration templates. Several topologies use Linux containers as attached devices. You must have a working *containerlab* installation and use *libvirt* or *clab* provider to use those topologies.

The topology does not specify the virtualization provider or the device under test. Start the lab with

```
netlab up -p <provider> -d <device> <topology-file>
```

The topologies implement the following scenarios:

* `interfaces.yml` -- IPv4 and IPv6 addressing on loopback and physical interfaces, interface MTU, and bandwidth. Validation tests check IPv4 and IPv6 connectivity between attached Linux hosts.
* `loopback.yml` -- primary and additional loopbacks configured with IPv4 and IPv6 addresses. Validation tests check IPv4 and IPv6 connectivity between loopback interfaces and attached Linux hosts.
* `unnumbered.yml` -- unnumbered IPv4 and IPv6 interfaces.
