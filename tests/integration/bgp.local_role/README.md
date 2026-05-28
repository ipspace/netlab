# BGP local role integration test cases

This directory contains topologies that test the **bgp.local_role** plugin (RFC 9234 BGP Roles). The topologies use FRR containers as external BGP hosts; run the tests with the *clab* or *libvirt* provider.

Specify the device under test with environment variables:

```
$ export NETLAB_DEVICE=frr
$ export NETLAB_PROVIDER=clab
```
