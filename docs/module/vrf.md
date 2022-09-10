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

| Operating system      | VRF<br />config | Route<br />leaking | VRF-aware<br />OSPF | VRF-aware<br />EBGP | VRF-aware<br />Loopback |
| --------------------- | :-: | :-: | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cisco IOS             | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cisco IOS XE          | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cisco Nexus OS        | ✅  | ✅  | ✅  | ✅  | ✅  |
| Dell OS10             | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cumulus NVUE          | ✅  |  ❌  |  ❌  |  ❌  |  ❌  |
| Mikrotik CHR RouterOS | ✅  | ✅  | ✅  | ✅  |  ❌  |
| VyOS                  | ✅  | ✅  | ✅  | ✅  | ✅  |
| SR Linux              | ✅  | ✅* | ✅  | ✅  | ✅  |
| FRR [❗](../caveats.html#caveats-frr-config) | ✅  |  ❌  | ✅  |  ❌  | ✅  |

**Notes:**
* IS-IS cannot be run within a VRF, but the IS-IS configuration module is VRF-aware -- it will not try to configure IS-IS routing on VRF interfaces
* IBGP within a VRF instance does not work. PE-routers and CE-routers MUST HAVE different BGP AS numbers
* On Mikrotik RouterOS BGP configuration/implementation, a BGP VRF instance cannot have the same Router ID of the default one. The current configuration template uses the IP Address of the last interface in the VRF as instance Router ID.
* (*) On SR Linux, route leaking is supported only in combination with BGP EVPN

## Parameters

The following parameters can be set globally or per node:

* **vrfs**: A dictionary of VRF definitions (see below)
* **vrf.loopback** (bool): Create loopback interfaces for all VRFs on this node
* **vrf.as**: The default AS number used in RD/RT values when **bgp.as** is not set. The system default for **vrf.as** is 65000.

(module-vrf-definition)=
## VRF Definition

VRFs are defined in a global- or node-specific **vrfs** dictionary, allowing you to create VRFs that are used network-wide or VRFs that are used only on a single node.

```{warning}
Do not reuse VRF names when defining node-specific VRFs. There's a subtle interaction between global- and node-specific VRFs needed to implement complex VPN topologies.
```

The keys of the **vrfs** dictionary are VRF names, the values are VRF definitions. A VRF definition could be empty or a dictionary with one or more of these attributes:

* **rd** -- route distinguisher (integer or string)
* **import** -- a list of import route targets
* **export** -- a list of export route targets
* **loopback** (bool or prefix) -- Create a loopback interface for this VRF.

Empty VRF definition will get [default RD and RT values](default-vrf-values) assigned during the topology transformation process.

(vrf-loopback)=
### Creating VRF Loopback Interfaces

A loopback interface is created for a VRF whenever you set the **vrfs.*name*.loopback** or **vrf.loopback** global or node parameter.

**loopback** parameter in a VRF definition could be:

* A boolean value -- the address of the loopback interface will be allocated from the **vrf_loopback** address pool
* A string specifying the IPv4 prefix of the loopback interface
* A dictionary of address families specifying IPv4 and/or IPv6 prefixes to be used on the loopback interface

### RD and RT Values

A route distinguisher could be specified in N:N format (example: 65000:1) or as an integer. AS number specified in **bgp.as** or **vrf.as** will be prepended to an integer RD-value to generate RD value in N:N format.

**import** and **export** route targets could be specified as a single value or as a list of values. Each RT value could be an integer (see above), a string in N:N format, or a VRF name. When using a VRF name as an RT value, the VRF RD is used as the route target.

For example, to implement a common services VPN giving *red* and *blue* VRFs access to *common* VRF, use these VRF definitions:

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

The following default values are used in VRF definitions missing **rd**, **import** or **export** values (including the corner case of empty VRF definition):

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

* Global RD/RT values are generated using the system default **vrf.as** value (65000).
* Global RT values for the *red* VRF are copied into the node data structures. Global RD value is not copied because it's set in the node VRF definition.
* Node RD value for the *red* VRF is generated using the node **bgp.as** value (65001).

(module-vrf-interface)=
## Using VRFs on Interfaces and Links

To use a VRF, add **vrf** attribute (global- or node-specific VRF name) to a link or an interface on a link.

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

While it usually makes sense to specify **vrf** on an interface, you could use **vrf** attribute on a link to add all interfaces attached to that link to the specified VRF, for example when building VRF-lite topologies.

## Interaction with Routing Protocols

BGP, OSPF, and IS-IS configuration modules are VRF aware:

* VRF interfaces are removed from the IS-IS routing process
* VRF interfaces that should be part of an OSPF routing process are moved into VRF-specific data structures that are then used to create VRF-specific OSPF instances.
* EBGP neighbors discovered on VRF interfaces are moved into VRF-specific data structures and used to configure BGP neighbors with a BGP VRF address family.

Notes:

* VRF OSPF instances are created only in VRFs that have neighbors using **ospf**  configuration module. To create an OSPF instance in a VRF that would need OSPF based on the lab topology, set **ospf.active** node VRF parameter to *True*.
* VRF-specific OSPF and BGP configuration is included in the VRF configuration templates.
* Connected subnets are always redistributed into the BGP VRF address family.
* If a node has **bgp.as** parameter and VRF-specific OSPF instance(s), the VRF configuration templates configure two-way redistribution between VRF-specific OSPF instances and BGP VRF address family.

### Creating VRF OSPF Instances

Assume that we want to have OSPF instance in the brown VRF, but the only link in the VRF is a stub link, so the OSPF instance would not be created with default settings. Setting **ospf.active** parameter in **nodes.r3.vrfs.brown** forces the creation of VRF OSPF instance.

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

You'll find a half-dozen examples in the [Defining and Using VRFs](../example/vrf-tutorial.md) tutorial.
