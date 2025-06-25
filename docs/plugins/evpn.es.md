(plugin-evpn-es)=
# EVPN Ethernet Segment (EVPN Multihoming)

This plugin allows for simple EVPN Ethernet Segment configuration, also know as EVPN Multihoming.

For now, the plugin supports:
* ES definition on LAG or "physical" interfaces (depending on platform support)
* Only `all-active` multihoming
* Manual or Auto-Generated (based on LACP) Ethernet Segment Identifier

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | ES on LAG (ESI-LAG) | ES on other interfaces | Auto ESI |
| ------------------- | :--: | :--: | :--: |
| Arista EOS          |  ✅  |  ✅  |  ✅  |
| vJunos Switch       |  ✅  |  ✅  |  ✅  |


## Using the Plugin

* Add `plugin: [ evpn.es ]` to the lab topology.
* Define a set of *ethernet segments* on the topology top-level
* Include the **evpn.es** attribute in the device interface

### Supported attributes

The plugin adds the following attributes defined at topology level:
* **evpn.ethernet_segments** (dict) -- Key is the **ethernet segment** name. Each item is a *dict* with the following attributes:
    * **id** (esi_id, mandatory) -- ESI in format `00:XX:XX:XX:XX:XX:XX:XX:XX:XX` (only Type-0 ESI is supported for now)
    * **auto** (bool) -- Use ESI auto generation based on LACP System ID. If both `id` and `auto` are specified, explicit `id` takes over.

Interface level attributes:
* **evpn.es** (str) -- ethernet segment name as defined on `evpn.ethernet_segments`.

## Example

```
plugin: [ 'evpn.es' ]

defaults.vxlan.start_vni: 20000
bgp.as: 65000

evpn.ethernet_segments:
  seg_1.id: 00:11:22:33:44:55:66:77:88:99

groups:
  _auto_create: true
  switches:
    members: [ s1, s2 ]
    module: [ vlan, vxlan, ospf, bgp, evpn, lag ]
  probes:
    members: [ x1 ]
    module: [ lag, vlan ]
    device: eos
  hosts:
    members: [ h1, h2, h3 ]
    device: linux
    provider: clab

vlans:
  red:
    mode: bridge
    links: [ h1-x1, h2-s1, h3-s2 ]

links:
# EVPN/VXLAN Switch to Switch Link
- s1:
  s2:
  mtu: 1600
# ESI-LAG
- lag:
    members:
    - s1:
        lag.lacp_system_id: 1
        evpn.es: seg_1
      x1:
    - s2:
        lag.lacp_system_id: 1
        evpn.es: seg_1
      x1:
  vlan.access: red
```
