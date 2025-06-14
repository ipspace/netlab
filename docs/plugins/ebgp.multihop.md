(plugin-ebgp-multihop)=
# Multihop EBGP

The **ebgp.multihop** plugin adds support for multihop EBGP sessions established between loopback interfaces of routers in different autonomous systems.

The plugin implements multihop EBGP sessions in the global routing table. VRF multihop EBGP sessions are not implemented yet.

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | Global<br>sessions | VRF<br>sessions |
| ------------------- | :--: | :--: |
| Aruba AOS-CX        |  ✅  |  ✅  |
| Arista EOS          |  ✅  |  ✅  |
| Cisco IOSv/IOS-XE[^18v] | ✅ | ✅ |
| Cumulus Linux 4.x   |  ✅  |  ✅  |
| Cumulus 5.x (NVUE)  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |
| JunOS               |  ✅  |  ✅  |
| Nokia SR Linux      |  ✅  |  ❌   |
| Nokia SR OS         |  ✅  |  ✅  |

[^18v]: Includes Cisco IOSv, Cisco IOSvL2, Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

## Specifying Multihop EBGP Sessions

Multihop EBGP sessions are specified in the global **bgp.multihop.sessions** list. Individual elements of the list can take any valid [link format](link-formats), from strings to dictionaries, for example:

```
bgp.multihop.sessions:
- r1-r2
- r1:
  r3:
```

```{warning}
It might be possible specify more than two nodes in a list entry to create a full mesh of multihop EBGP sessions, but don't complain if it doesn't work -- that trick is unsupported.
```

Additional parameters specified on a BGP session or on individual nodes participating in a BGP session are converted into BGP parameters. For example, you could specify **local_as** on a node participating in an EBGP multihop session:

```
bgp.multihop.sessions:
- r1:
    local_as: 65101
  r2:
```

## Integration with Other BGP Plugins

EBGP multihop plugin works together with **[bgp.session](bgp.session.md)** and **[bgp.policy](bgp.policy.md)** plugins, but has to be listed after them in the list of plugins:

```
plugin: [ bgp.session, ebgp.multihop ]

bgp.multihop.sessions:
- r1:
    local_as: 65101
  r2:
```

You can specify any attribute supported by the other BGP plugins on an EBGP multihop session (assuming you included both plugins in your topology).

```
plugin: [ bgp.session, ebgp.multihop ]

bgp.multihop.sessions:
- r1:
    local_as: 65101
  r2:
  password: Secret
```

## Activation of Individual Address Families

You can use the global **bgp.multihop.activate** dictionary to enable selective activation of BGP address families on EBGP multihop sessions. The address families active on EBGP multihop sessions can be specified for **ipv4** and **ipv6** neighbors.

For example, to implement the (infamous) EBGP-over-EBGP EVPN design, use the following configuration. The **bgp.multihop.activate.ipv4** setting will disable IPv4 address family on EBGP multihop sessions and enable EVPN on them.

```
bgp:
  community.ebgp: [ standard, extended ]
  multihop:
    sessions: [ leaf1-leaf2 ]
    activate: 
      ipv4: [ evpn ]
``
