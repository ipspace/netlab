# Virtual Routing and Forwarding (VRF) Tables

This configuration module implements the VRF planning and configuration logic and is used together with [BGP](bgp.md), [OSPF](ospf.md), and [IS-IS](isis.md) configuration modules to implement VRF-aware routing protocols.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

(module-vrf-platform-support)=
VRFs are supported on these platforms:

| Operating system      | VRF<br />config | Route<br />leaking |  VRF-aware<br />Loopback |
| --------------------- | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  | ✅  | ✅  |
| Cisco IOS             | ✅  | ✅  | ✅  |
| Cisco IOS XE          | ✅  | ✅  | ✅  |
| Cisco Nexus OS        | ✅  | ✅  | ✅  |
| Cumulus Linux         | ✅  | ✅  | ✅  |
| Cumulus NVUE          | ✅  |  ❌  |  ❌  |
| Dell OS10             | ✅  | ✅  | ✅  |
| FRR [❗](caveats-frr) | ✅  | ✅  | ✅  |
| Juniper vMX           | ✅  | ✅  | ✅  |
| Juniper vPTX          | ✅  | ✅  | ✅  |
| Juniper vSRX 3.0      | ✅  | ✅  | ✅  |
| Mikrotik RouterOS 6   | ✅  | ✅  |  ❌  |
| Mikrotik RouterOS 7   | ✅  | ✅  | ✅  |
| SR Linux              | ✅  | ✅ [❗](caveats-srlinux) | ✅  |
| VyOS                  | ✅  | ✅  | ✅  |

(module-vrf-platform-routing-support)=
These platforms support routing protocols in VRFs:

| Operating system      | VRF-aware<br />OSPF | VRF-aware<br />OSPFv3 | VRF-aware<br />EBGP |
| --------------------- | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  |  ❌  | ✅  |
| Cisco IOS             | ✅ [❗](caveats-iosv) | ✅  | ✅  |
| Cisco IOS XE          | ✅ [❗](caveats-csr) | ✅  | ✅  |
| Cisco Nexus OS        | ✅  |  ❌  | ✅  |
| Cumulus Linux         | ✅  |  ❌  | ✅  |
| Dell OS10             | ✅  |  ❌  | ✅  |
| FRR [❗](caveats-frr) | ✅  | ✅  | ✅  |
| Juniper vMX           | ✅  | ✅  | ✅  |
| Juniper vPTX          | ✅  | ✅  | ✅  |
| Juniper vSRX 3.0      | ✅  | ✅  | ✅  |
| Mikrotik RouterOS 6   | ✅  [❗](caveats-routeros6) |  ❌  | ✅  |
| Mikrotik RouterOS 7   | ✅  |  ❌  | ✅  |
| SR Linux              | ✅  |  ❌  | ✅  |
| VyOS                  | ✅  |  ❌  | ✅  |

```{note}
* IS-IS and EIGRP cannot be run within a VRF, but both configuration modules are VRF-aware -- they will not try to configure IS-IS or EIGRP routing on VRF interfaces
* IBGP within a VRF instance does not work. PE-routers and CE-routers MUST HAVE different BGP AS numbers
* See [VRF Integration Tests Results](https://release.netlab.tools/_html/coverage.vrf) for more details.
```

## Parameters

The following parameters can be set globally or per node:

* **vrfs**: A dictionary of VRF definitions (see below)
* **vrf.loopback** (bool): Create loopback interfaces for all VRFs used on this node
* **vrf.as**: The default AS number used in RD/RT values when **bgp.as** is not set. The system default for **vrf.as** is 65000.

(module-vrf-definition)=
## VRF Definition

VRFs are defined in a global or node-specific **vrfs** dictionary, allowing you to create VRFs that are used network-wide or only on a single node.

The keys of the **vrfs** dictionary are VRF names; the values are VRF definitions. A VRF definition could be empty or a dictionary with one or more of these attributes:

* **rd** -- route distinguisher (integer or string)
* **import** -- a list of import route targets
* **export** -- a list of export route targets
* **loopback** (bool or prefix) -- Create a loopback interface for this VRF.
* **links** - a [list of links](module-vrf-links) within this VRF.
* A VRF definition can also contain other link- or interface-level parameters (for example, OSPF cost).

Empty VRF definition will get [default RD and RT values](default-vrf-values) assigned during the topology transformation process.

```{warning}
* Do not reuse VRF names when defining node-specific VRFs. To implement complex VPN topologies, a subtle interaction between global and node-specific VRFs is needed, and _netlab_ assumes that the VRFs with the same name refer to the same routing and forwarding instance.
* Global VRFs will not be instantiated on a node using the _vrf_ module unless the node is attached to a [VRF link](module-vrf-interface). If you want to create a VRF that uses no external interfaces, add the VRF name to the node **‌vrfs** dictionary.
* The **‌vrfs** dictionary and the _vrf_ module will be removed from a node with no VRF interfaces or [VRF loopback interfaces](vrf-loopback).
```


### Additional VRF Parameters

You can also set these parameters to influence routing protocols within a VRF.

* **ospf.active** -- start an OSPF instance within a VRF even when there are no viable OSPF neighbors on VRF interfaces
* **ospf.area** -- the default OSPF area for the VRF OSPF process (default: node **ospf.area**). It is configured on the VRF loopback interfaces.
* **bgp.router_id** -- per-VRF BGP router ID. You have to set this parameter if you want to configure inter-VRF EBGP sessions between interfaces of the same device.[^ELB]
* **ospf.router_id** -- per-VRF OSPF router ID. You can use this parameter for the same reasons as **bgp.router_id** or if you want consistent OSPF router IDs on Cisco IOS.

[^ELB]: That's how some people implement inter-VRF route leaking. You don't want to know the details ;)

(vrf-loopback)=
### Creating VRF Loopback Interfaces

A loopback interface is created for a VRF whenever you set the **vrfs.*name*.loopback** or **vrf.loopback** global or node parameter.

**loopback** parameter in a VRF definition could be:

* A boolean value -- the address of the loopback interface will be allocated from the **vrf_loopback** address pool
* A string specifying the IPv4 prefix of the loopback interface
* A dictionary of address families specifying IPv4 and/or IPv6 prefixes to be used on the loopback interface

```{warning}
The explicit IPv4/IPv6 loopback addresses should be used only in the node VRF definition, not in the global VRF definition.
```

### RD and RT Values

A route distinguisher could be specified in N:N format (example: 65000:1) or as an integer. AS number specified in **bgp.as** or **vrf.as** will be prepended to an integer RD-value to generate RD value in N:N format.

**import** and **export** route targets could be specified as a single value or a list of values. Each RT value could be an integer (see above), a string in N:N format, or a VRF name. When using a VRF name as an RT value, the VRF RD is used as the route target.

For example, to implement a _common services_ VPN giving *red* and *blue* VRFs access to *common* VRF, use these VRF definitions:

```
vrfs:
  red:
    import: [ red, common ]
    export: [ red ]
  blue:
    import: [ blue, common ]
    export: [ blue ]
  common:
    import: [ common, red, blue ]
    export: [ common ]
```

(default-vrf-values)=
### Default RD/RT Values

The following default values are used in VRF definitions missing **rd**, **import**, or **export** values (including the corner case of empty VRF definition):

* VRFs specified in nodes inherit missing parameters from the global VRFs with the same name
* When the **rd** is missing, it's assigned a unique value using **bgp.as** or **vrf.as** value as the high-end of the RD value
* Missing **import** and **export** route targets become a list with the VRF RD being the sole element.

For example, defining a simple VRF *red*...

```
vrfs:
  red:
```

... results in the following data structure:

```
vrfs:
  red:
    export:
    - '65000:1'
    import:
    - '65000:1'
    rd: '65000:1'
```

When using an empty **rd** value in a node VRF, the **rd** will be auto-generated, while the **import** and **export** route targets will be inherited from the global VRF definition.

For example, defining a *red* VRF with node-specific RD...

```
vrfs:
  red:

nodes:
  r1:
    bgp.as: 65001
    vrfs.red.rd:
```

... results in the following (VRF-related) data structures:

```
vrfs:
  red:
    export:
    - '65000:1'
    import:
    - '65000:1'
    rd: '65000:1'

nodes:
  r1:
    vrfs:
      green:
      red:
        export:
        - '65000:1'
        import:
        - '65000:1'
        rd: '65001:2'
```

Notes:

* The global RD/RT values are generated using the system default **vrf.as** value (65000).
* The global RT values for the *red* VRF are copied into the node data structures. The global RD value is not copied because it's set in the node VRF definition.
* Node RD value for the *red* VRF is generated using the node **bgp.as** value (65001).

(module-vrf-interface)=
## Using VRFs on Interfaces and Links

To use a VRF, add the **vrf** attribute (a global or node-specific VRF name) to a link or an interface on a link.

For example, the following topology creates a simple VRF with two hosts attached to it:

```
module: [ vrf ]

vrfs:
  red:

nodes:
  r1:
    device: eos
  h1:
    device: linux
  h2:
    device: linux

links:
- r1:
    vrf: red
  h1:
- r1:
    vrf: red
  h2:
```

While it usually makes sense to specify **vrf** on an interface, you could use the **vrf** attribute on a link to add all interfaces attached to that link to the specified VRF, for example, when building VRF-lite topologies.

(module-vrf-links)=
### Specify Links within VRF Definition

While you can assign links to VRFs with the **vrf** link or interface attribute, you can also list VRF links in the **links** list of a global VRF definition. The methods are equivalent and produce the same results, but the VRF **links** approach results in a more concise lab topology.

Consider the simplest possible topology with a switch (s1) and two hosts (h1 and h2) connected to two interfaces in the same VRF. This is how you would define the VRF and links within that VRF:

```
vrfs:
  example:
  
links:
- h1:
  s1:
  vrf: example
- h2:
  s1:
  vrf: example
```

Using the VRF **links** attribute, the same lab topology could be (using [link definition shortcuts](link-example-no-attributes)) shortened to:

```
vrfs:
  example:
    links: [ h1-s1, h2-s1 ]
```

## Interaction with Routing Protocols

BGP, OSPF, and IS-IS configuration modules are VRF aware:

* VRF interfaces are removed from the IS-IS routing process
* VRF interfaces that should be part of an OSPF routing process are moved into VRF-specific data structures that are then used to create VRF-specific OSPF instances.
* EBGP neighbors discovered on VRF interfaces are moved into VRF-specific data structures and used to configure BGP neighbors with a BGP VRF address family.

Notes:

* VRF OSPF instances are created only in VRFs with neighbors using the **ospf**  configuration module. To create an OSPF instance in a VRF that would need OSPF based on the lab topology, set the **ospf.active** node VRF parameter to *True*.
* VRF-specific OSPF and BGP configurations are included in the VRF configuration templates.
* Connected subnets are redistributed into the OSPF VRF routing process and the BGP VRF address family.
* If a node has **bgp.as** parameter and VRF-specific OSPF instance(s), the VRF configuration templates configure two-way redistribution between them and the BGP VRF address family.

### Creating VRF OSPF Instances

Assume that we want an OSPF instance in the brown VRF, but the only link in the VRF is a stub link, so the OSPF instance would not be created with default settings. Setting the **ospf.active** parameter in **nodes.r3.vrfs.brown** forces the creation of the VRF OSPF instance.

```
nodes:
  r3:
    module: [ vrf,ospf ]
    vrfs:
      brown:
        ospf.active: True

links:
- r3:
    vrf: brown
```

## Examples

You'll find VRF-related examples in the [Defining and Using VRFs](../example/vrf-tutorial.md) tutorial and in these blog posts:

-   [Creating VRF Lite Labs With netlab](https://blog.ipspace.net/2022/04/netsim-vrf-lite.html)
-   [Creating MPLS/VPN Labs With netlab](https://blog.ipspace.net/2022/04/netsim-mpls-vpn.html)
-   [Combining VLANs with VRFs](https://blog.ipspace.net/2022/06/netsim-vlan-vrf.html){style="-webkit-font-smoothing: antialiased; color: rgb(210, 100, 0); text-decoration: none; transition: color 0.3s ease-in-out 0s;"}
-   [VRF Lite Topology with VLAN Trunks](https://blog.ipspace.net/2022/09/netlab-vrf-lite.html)
-   [Using VLAN and VRF Links](https://blog.ipspace.net/2023/04/netlab-vrf-vlan-links.html)
