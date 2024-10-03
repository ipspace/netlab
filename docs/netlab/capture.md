(netlab-capture)=
# Packet Capture

The **netlab capture** command can be used to capture packets on [*libvirt* virtual machines](libvirt-capture) or [*containerlab*-created Docker containers](lab-clab). The default packet capturing program is `tcpdump`; you can change that with the [default settings](defaults).

```{warning}
You cannot capture traffic on point-to-point links between *‌libvirt* virtual machines; you have to change them into Linux bridges ([more details](libvirt-capture)).
```

## Usage

The **netlab capture** command takes two parameters: the node you want to perform packet capture on and the interface name within that node.

```text
$ netlab capture -h
usage: netlab capture [-h] [--snapshot [SNAPSHOT]] node [intf]

Start a packet capture on the specified node/interface

positional arguments:
  node                  Node on which you want to capture traffic
  intf                  Interface on which you want to capture traffic

options:
  -h, --help            show this help message and exit
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file

All other arguments are passed directly to the packet-capturing utility
```

## Examples

Let's assume we're using this simple topology:

```
defaults.device: cumulus
provider: clab

module: [ ospf ]
nodes: [ r1, r2 ]
links: [ r1-r2 ]
```

After starting the lab, you can use the **netlab capture r1 swp1** command to capture all the traffic on the R1-R2 link:

```bash
$ netlab capture r1 swp1
Starting packet capture on r1/swp1: sudo ip netns exec clab-X-r1 tcpdump -i swp1 -l -v
tcpdump: listening on swp1, link-type EN10MB (Ethernet), snapshot length 262144 bytes
17:37:39.031667 IP6 (flowlabel 0xa854f, hlim 255, next-header ICMPv6 (58) payload length: 24) fe80::a8c1:abff:fe84:1dfb > ip6-allnodes: [icmp6 sum ok] ICMP6, router advertisement, length 24
	hop limit 64, Flags [none], pref medium, router lifetime 15s, reachable time 0ms, retrans timer 0ms
	  source link-address option (1), length 8 (1): aa:c1:ab:84:1d:fb
```

```{tip}
If you don't specify additional parameters, **‌netlab capture** adds `-l -v` (unbuffered, verbose) flags to the **tcpdump** command line
```

If you want to capture a subset of traffic, use **tcpdump** traffic filters (you will also have to specify the `-l -v` flags if you wish to have an immediate verbose printout). For example, you can use the following command to display OSPF traffic:

```bash
$ netlab capture r1 swp1 proto ospf -l -v
Starting packet capture on r1/swp1: sudo ip netns exec clab-X-r1 tcpdump -i swp1 proto ospf -l -v
tcpdump: listening on swp1, link-type EN10MB (Ethernet), snapshot length 262144 bytes
17:39:30.143019 IP (tos 0xc0, ttl 1, id 42863, offset 0, flags [none], proto OSPF (89), length 68)
    10.1.0.2 > 224.0.0.5: OSPFv2, Hello, length 48
	Router-ID 10.0.0.2, Backbone Area, Authentication Type: none (0)
	Options [External]
	  Hello Timer 10s, Dead Timer 40s, Mask 255.255.255.252, Priority 1
	  Neighbor List:
	    10.0.0.1
```

## Changing the Packet-Capturing Utility

**netlab capture** uses **tcpdump** as the default packet-capturing utility. You can change that with the **defaults.netlab.capture.command** parameter ([default changing details](defaults)). The command you specify must include the `{intf}` string at the point where the packet-capturing utility expects the interface name.

To change the default parameters passed to the packet-capturing utility, change the **defaults.netlab.capture.command_args** parameter.

To display the default settings, use the ‌**‌netlab show defaults netlab.capture** command.

```bash
$ netlab show defaults netlab.capture

netlab default settings within the netlab.capture subtree
=============================================================================

command: tcpdump -i {intf}
command_args: -l -v
```

