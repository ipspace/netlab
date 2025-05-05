(example-bridge)=
# Building a Multi-Access Network with a Bridge Node

Testing failure scenarios in virtual networks is a bit harder than in the real world. Shutting down an interface [might bring down adjacent interfaces](https://blog.ipspace.net/2025/03/arista-spooky-action-distance/), or trigger an interface-down event on the remote node if you're connecting devices with vEth pairs. Even worse, some devices might reenable interfaces you try to shut down with **ip link set down** Linux command instead of the **shutdown** configuration command.

Inserting a virtual bridge between adjacent virtual machines with the **type: lan** link attribute solves some of the abovementioned problems. If you shut down the interface connected to the virtual bridge with the **ip link set _interface_ down** command, you usually experience similar effects to transceiver/switch failure in the real world -- the node interface is *up*, but it cannot receive or send any traffic. Unfortunately, you cannot use the same approach for point-to-point links between containers (_netlab_ never uses a Linux bridge for point-to-point container links); you must attach an extra node to the link to force _netlab_ to use a Linux bridge.

Even though you could use the *Linux bridge* trick to get host interfaces you can shut down, you must be familiar with Linux networking commands to find the bridge and attached interface names, and to shut down the desired interface.

_netlab_ release 2.0 allows you to replace a Linux bridge in a multi-access network with another lab device (VM or container) with **role: bridge** attribute. The rules are straightforward:

* Add another node to the lab topology with the **role: bridge** attribute. The device you use for the bridge must [support the **bridge** role](platform-host).

For example, in the following topology, you would get an Arista EOS container acting as a simple bridge inserted between two FRR routers:

```
provider: clab
defaults.device: frr

nodes:
  a:
  b:
  br:
    role: bridge
    device: eos

links:
- a:
  b:
  bridge: br
```

After starting the lab, the following configuration is deployed on the Arista EOS **br** node (only the relevant parts are included in the printout):

```
vlan 100
   name br_vlan_100
!
interface Ethernet1
   description [Access VLAN br_vlan_100] br -> a
   mac-address 52:dc:ca:fe:03:01
   switchport access vlan 100
!
interface Ethernet2
   description [Access VLAN br_vlan_100] br -> b
   mac-address 52:dc:ca:fe:03:02
   switchport access vlan 100
```

You can now shut down an interface on the **br** node using familiar configuration commands (manually, using **netlab config**, or with a **[validate](validate)** **config** action) to emulate a link loss.

## Using a Bridge Node in a Validation Test

Here's an example (taken from the [VRRP integration test](https://github.com/ipspace/netlab/blob/dev/tests/integration/gateway/02-vrrp.yml)) of using a **bridge** node in a validation test:

* The lab topology uses a link implemented with a Linux container acting as a bridge device (we have to use a bridge node because the validation tests cannot execute commands on the host):

```
links:
- bridge: br_a       # Use an explicit Linux bridge on the client network
  h1:
  dut:
    gateway.vrrp.priority: 30
  r2:
    gateway.vrrp.priority: 20
  gateway: True
  prefix: source
```

* A [custom configuration template](https://github.com/ipspace/netlab/blob/dev/tests/integration/gateway/linkdown/linux.j2) finds the Linux interface with the desired neighbor (specified in the Ansible **neighbor** variable) and shuts it down (it has to match the **neighbor** value with the **node** attribute of entries in the **intf.neighbors** list):

```
#!/bin/bash
{% for intf in interfaces
     if neighbor in intf.neighbors|map(attribute='node',default='')
       and intf.vlan.access_id is defined %}
ip link set {{ intf.ifname }} {{ ifstate|default('down') }}
{% endfor %}
```

* The custom configuration template [is used](validate-config) in [validation tests](validate-tests) to disconnect a node from the LAN segment and reconnect it:

```
validate:
  r2_disconnect:
    description: Disable R2 link on client LAN
    nodes: [ br_a ]
    config:
      template: linkdown
      variable.neighbor: r2
      variable.ifstate: 'down'
    pass: R2 link has been disabled on client LAN
    stop_on_error: True
...
  r2_reconnect:
    description: Reconnect R2 to the client LAN
    nodes: [ br_a ]
    config:
      template: linkdown
      variable.neighbor: r2
      variable.ifstate: 'up'
    pass: R2 has been reconnected to client LAN
    stop_on_error: True
```
