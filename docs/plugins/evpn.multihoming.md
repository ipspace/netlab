(plugin-evpn-multihoming)=
# EVPN Multihoming (EVPN Ethernet Segment)

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
| Cumulus NVUE        |  ✅  |  ❌  |  ❌  |
| vJunos Switch       |  ✅  |  ✅  |  ✅  |


## Using the Plugin (auto mode)

* Add `plugin: [ evpn.multihoming ]` to the lab topology.
* Include the **evpn.es** attribute in the device interface

netlab will generate, for each *Ethernet Segment*, ESI value (*Ethernet Segment ID*) and LACP System ID (for *ESI-LAG*).

**NOTE**: Ethernet Segments ID will be generated starting from an integer value, which will be used as the first 5 most significant bytes (excluding the initial `0x00`). This is to:

* be able to generate a 6-bytes LACP System ID starting with `0x02`.
* be able to generate unique *ES-Import* target for each auto generated ESI value.

## Using the Plugin (manual mode)

It is also possible to manually define ESI values for your *Ethernet Segments*. In that case:

* Add `plugin: [ evpn.multihoming ]` to the lab topology.
* Define a set of *ethernet segments* on the topology top-level
* Include the **evpn.es** attribute in the device interface

**NOTE**: EVPN Multihoming, for ESI-LAG, requires that all LAG interfaces belonging to the same *ethernet segment* share the same (unique) LACP System ID. This can be achieved using the `lag.lacp_system_id` attribute - which can accept a "real" mac address value or an integer (*1-65535*) value: in that case it will generate a mac value in the format `02:xx:yy:xx:yy:00` (i.e., `1` will become `02:00:01:00:01:00`).

### Supported attributes

The plugin adds the following attributes defined at topology level:
* **evpn.ethernet_segments** (dict) -- Key is the **ethernet segment** name. Each item is a *dict* with the following attributes:
    * **id** (esi_id, mandatory) -- ESI in format `00:XX:XX:XX:XX:XX:XX:XX:XX:XX` (only Type-0 ESI is supported for now)
    * **auto** (bool) -- Use ESI auto generation based on LACP System ID. If both `id` and `auto` are specified, explicit `id` takes over.

Interface level attributes:
* **evpn.es** (str) -- ethernet segment name (can be defined on `evpn.ethernet_segments`).

## Example (auto mode)

```
plugin: [ 'evpn.multihoming' ]

bgp.as: 65000

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
        evpn.es: seg_1
      x1:
    - s2:
        evpn.es: seg_1
      x1:
  vlan.access: red
```

## Example (manual mode)

```
plugin: [ 'evpn.multihoming' ]

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
