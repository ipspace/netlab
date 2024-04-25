# BGP integration test cases

This directory contains numerous topologies that test most of the attributes supported by the **bgp.session** plugin[^MT]. The topologies use FRR containers as the external BGP hosts; you should run the tests using the *libvirt* or *clab* virtualization provider.

[^MT]: The mapping between topology names and attributes should be trivial.

The topology does not specify the virtualization provider and the device under test. The easiest way to specify them is to use environment variables:

```
$ export NETLAB_DEVICE=<device-type>
$ export NETLAB_PROVIDER=<provider-type>
```
