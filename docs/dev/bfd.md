# BFD Configuration Templates

This document describes BFD configuration module implementation details:

* Typical BFD interface configuration template
* Data structures describing IGP BFD client state
* Typical configuration template enabling IGP BFD client in individual interfaces

## BFD Configuration Template Boilerplate

When configuring BFD on an interface, you have to consider global and interface BFD parameters as well as whether BFD is disabled on an interface with **bfd: false**:

* Global BFD parameters are in **bfd** variable. At least **bfd.multiplier** is set in the global parameters (from system defaults)
* Interface BFD parameters are in **l.bfd** variable
* BFD is disabled when **l.bfd** is defined and has a *False* (or *None* or empty) value.
* You could specify default platform values for **bfd.min_rx** and **bfd.min_tx** in **devices._device_.bfd** system settings or in the configuration template.

```
{% for l in links|default([]) if bfd|default(False) or l.bfd|default(False) %}
interface {{ l.ifname }}
{%   set disable_bfd = l.bfd is defined and not l.bfd %}
{%   if not disable_bfd %}
{%     set link_bfd = l.bfd|default({}) %}
 bfd interval {{ 
   link_bfd.min_tx|default(bfd.min_tx)|default(500) }} min_rx {{ 
   link_bfd.min_rx|default(bfd.min_rx)|default(500) }} multiplier {{
   link_bfd.multiplier|default(bfd.multiplier)|default(3)
   }}
!
{%   else %}
 no bfd interval
{%   endif %}
{% endfor %}
{% if bfd.min_echo_rx|default(0) %}
bfd slow-timers {{ bfd.min_echo_rx }} 
{% endif %}
```

## IGP/BFD Interaction

There are so many corner cases in BFD-with-IGP configuration matrix that it turned out to be simpler to calculate target IGP BFD state in the transformation code than to try to figure it out in Jinja2 configuration templates.

Inputs:

* Target BFD interface state -- *True* or *False*. Set with **bfd** link- or interface parameter. BFD is enabled on all interfaces whenever the BFD module is added to a node and can be disable on individual links/interface with **bfd: false**
* IGP BFD state -- Set with **igp.bfd** node parameter, for example **ospf.bfd** or **isis.bfd**. It can be a boolean value or a list of address families for multi-protocol IGPs (example: IS-IS).
* Interface IGP BFD state -- set with **igp.bfd** link- or interface parameter.

Output:

* Target interface IGP BFD state in **igp.bfd** interface parameter -- boolean value for single-AF routing protocols (OSPF, OSPFv3), AF dictionary for multi-AF routing protocols (IS-IS). You can use that parameter directly in device configuration templates (examples below).

Please note that the Python code calculating final IGP/BFD interface state updates only the interface data within **nodes**  but not links or node-on-link data.

Most combinations of input parameters are covered in `tests/topology/input/isis-bfd-test.yml`, here are just a few examples. Starting with a topology that has IPv6 enabled on P2P interfaces and runs IS-IS BFD for IPv4 and IPv6:

```
addressing: # Enable IPv6 on links
  p2p:
    ipv6: 2001:db8:1::/48

isis:
  area: 49.0002
  bfd:
    ipv4: True
    ipv6: True

module: [ isis, bfd ]

provider: clab

nodes:
- name: sros_r1
  device: sros
- name: srlinux_r2
  device: srlinux
```

Links with no parameters will have IS-IS BFD enabled for IPv4 and IPv6:

```
links:
- name: Regular link, BFD enabled
  sros_r1:
  srlinux_r2:
```

Sample interface data:

```
- ifindex: 1
  ifname: ethernet-1/1
  ipv4: 10.1.0.1/30
  ipv6: 2001:db8:1::1/64
  isis:
    bfd:
      ipv4: true
      ipv6: true
  linkindex: 1
  name: Regular link, BFD enabled
  neighbors:
    sros_r1:
      ifname: 1/1/c1
      ipv4: 10.1.0.2/30
      ipv6: 2001:db8:1::2/64
  provider_ifname: e1-1
  remote_id: 1
  remote_ifindex: 1
  type: p2p
```

Disabling BFD on a link removes **igp.bfd** parameter from the interface data:

```
- name: Link with BFD disabled
  sros_r1:
  srlinux_r2:
  bfd: False
```

```
- bfd: false
  ifindex: 2
  ifname: ethernet-1/2
  ipv4: 10.1.0.5/30
  ipv6: 2001:db8:1:1::1/64
  linkindex: 2
  name: Link with BFD disabled
  neighbors:
    sros_r1:
      ifname: 1/1/c2
      ipv4: 10.1.0.6/30
      ipv6: 2001:db8:1:1::2/64
  provider_ifname: e1-2
  remote_id: 1
  remote_ifindex: 2
  type: p2p
```

You get the same result if you disable BFD with IGP settings:

```
- name: Link with ISIS BFD disabled
  sros_r1:
  srlinux_r2:
  isis.bfd: False
```

In multi-AF routing protocols you could enable or disable BFD on each link/interface for individual address families:

```
- name: Link with IPv4-only BFD
  sros_r1:
  srlinux_r2:
  isis.bfd: { ipv4: True, ipv6: False }
```

Resulting interface data:

```
- ifindex: 4
  ifname: ethernet-1/4
  ipv4: 10.1.0.13/30
  ipv6: 2001:db8:1:3::1/64
  isis:
    bfd:
      ipv4: true
      ipv6: false
  linkindex: 4
  name: Link with IPv4-only BFD
  neighbors:
    sros_r1:
      ifname: 1/1/c4
      ipv4: 10.1.0.14/30
      ipv6: 2001:db8:1:3::2/64
  provider_ifname: e1-4
  remote_id: 1
  remote_ifindex: 4
  type: p2p
```


## IGP BFD Configuration Template Boilerplate

Adding BFD to an IGP configuration template is trivial due to already-computed interface BFD state.

Single-protocol boilerplate:

```
{% for l in links|default([]) %}
...
{%     if l.ospf.bfd|default(False) %}
 ip ospf bfd
{%     endif %}
...
{% endfor %}
```

Multi-protocol boilerplate:

```
{% for l in links|default([]) %}
...
{%     if l.isis.bfd.ipv4|default(False) %}
 isis bfd
{%     endif %}
{%     if l.isis.bfd.ipv6|default(False) %}
 isis ipv6 bfd
{%     endif %}
...
{% endfor %}
```
