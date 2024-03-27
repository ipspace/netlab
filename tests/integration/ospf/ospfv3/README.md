# OSPFv3 integration test cases

This directory contains numerous topologies you can use to test your OSPFv3 implementation. The topologies use FRR containers as the external OSPF hosts; you should run the tests using the *libvirt* or *clab* virtualization provider.

The topology does not specify the virtualization provider and the device under test. The easiest way to specify them is to use environment variables:

```
$ export NETLAB_DEVICE=<device-type>
$ export NETLAB_PROVIDER=<provider-type>
```

You can run the following tests:

* `01-network.yml` -- Tests the **broadcast** and **point-to-point** OSPFv3 network types. The **point-to-multipoint** and **non-broadcast** network types are not tested
* `02-areas.yml` -- Tests OSPFv3 areas and ABR functionality
* `03-cost.yml` -- Tests OSPFv3 interface costs
* `04-passive.yml` -- Tests passive and stub OSPFv3 interfaces
* `05-unnumbered.yml` -- Tests OSPFv3 on IPv6 LLA interfaces.

Each test includes a validation suite that can be run with the `netlab validate` command.

You can also run these tests (unfortunately without validation support):

* `bfd.yml` -- Tests OSPF with BFD

