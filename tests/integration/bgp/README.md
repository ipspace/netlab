# BGP integration test cases

This directory contains numerous topologies you can use to test your BGP implementation. The topologies use FRR containers as the external BGP hosts; you should run the tests using the *libvirt* or *clab* virtualization provider.

The topology does not specify the virtualization provider and the device under test. The easiest way to specify them is to use environment variables:

```
$ export NETLAB_DEVICE=<device-type>
$ export NETLAB_PROVIDER=<provider-type>
```

To test the 4-octet ASN support, change the default BGP ASN from 65000 to 80000:

```
$ export NETLAB_BGP_AS=80000
```

You can run the following IPv4-only tests:

* `01-ebgp-session.yml` -- Tests IPv4 EBGP sessions and route propagation
* `02-ibgp-ebgp-session.yml` -- Tests IPv4 EBGP and IBGP sessions and next-hop changes on IBGP session
* `03-ibgp-rr.yml` -- Tests IPv4 BGP route reflector functionality, reflection of inactive routes, and next-hop handling on reflected routes
* `04-originate.yml` -- Tests IPv4 BGP prefix origination from loopbacks, stub interfaces, and **bgp.originate** attribute.
* `05-community.yml` -- Tests propagation of BGP communities on IBGP and EBGP sessions
* `06-unnumbered.yml` -- Tests IPv4-only interface EBGP sessions (EBGP sessions over unnumbered IPv4 interfaces)
* `07-ebgp-localas.yml` -- Tests **local-as** functionality on EBGP sessions
* `08-ibgp-localas.yml` -- Tests **local-as** functionality that changes an EBGP session into an IBGP session.

You can run the following IPv6-only tests:

* `11-ipv6-ebgp.yml` -- Tests IPv6 EBGP sessions and route propagation
* `12-ipv6-ibgp-ebgp.yml` -- Tests IPv6 EBGP and IBGP sessions and next-hop changes on IBGP session
* `13-ipv6-ibgp-rr.yml` -- Tests IPv6 BGP route reflector functionality, reflection of inactive routes, and next-hop handling on reflected routes
* `14-ipv6-originate.yml` -- Tests IPv6 BGP prefix origination from loopbacks, stub interfaces, and **bgp.originate** attribute.
* `16-unnumbered.yml` -- Tests EBGP sessions over IPv6 LLA (interface EBGP sessions).

These tests can be used to validate the advanced dual-stack features:

* `20-dual-stack-activate.yml` -- Tests selective activation of default address families on IPv4 and IPv6 IBGP and EBGP sessions
* `21-dual-stack-unnumbered.yml` -- Tests IPv4 and IPv6 address families running over an interface EBGP session

All the above tests include a validation suite that can be run with the `netlab validate` command.


You can also run these tests:

* The integration tests for the **bgp.session** plugin are in the `session` directory.
* `bgp.domain.yml` -- Tests **bgp.domain** plugin (no validation)
* `ebgp.multihop.yml` -- Tests **bgp.multihop** plugin (no validation)
