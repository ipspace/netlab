# Ethernet Virtual Private Network (evpn) Configuration Module

This configuration module configures the EVPN address family for BGP, on Nokia SR OS, Nokia SR Linux and FRR.

The module depends on the BGP module.

## Parameters

* global: use_ibgp - whether to enable EVPN for iBGP(True,default) or eBGP neighbors

**Notes:**
* For iBGP peering (default) any ipv4/ipv6 address families towards iBGP peers are disabled, leaving an EVPN-only session
