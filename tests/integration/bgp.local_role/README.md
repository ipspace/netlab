# BGP local role integration test cases

This directory contains topologies that test the **bgp.local_role** plugin (RFC 9234 BGP Roles). The topologies use FRR containers as external BGP hosts; run the tests with the *clab* or *libvirt* provider.

Specify the device under test with environment variables:

```
$ export NETLAB_DEVICE=frr
$ export NETLAB_PROVIDER=clab
```

Validation tests run on the FRR probe nodes only, so the DUT can be FRR or BIRD.

The `01-provider-customer` topology includes an **upstream** provider that advertises a
prefix the DUT must not leak to the **peer** session (RFC 9234 OTC rules).
