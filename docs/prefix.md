(named-prefixes)=
# Named IP Prefixes

In most lab topologies, you probably don't care about the exact IP addresses and subnets. Defining IPv4 and IPv6 prefixes in [addressing pools](address pools) is good enough.

However, to tighten control over IP address allocation, you can use the **prefix** attribute on links or VLANS or the **ipv4**/**ipv6** attributes on node interfaces.

However, there are scenarios in which you have to use the same prefix in multiple places, for example:

* Using a link prefix in the lab validation code or in custom configuration templates
* Using a link prefix in a [prefix list](generic-routing-prefixes)
* Using the same prefix on multiple links, for example, to implement a stretched subnet using a technology not supported by _netlab_.

You can use *named IP prefixes* in all three scenarios. The named prefixes are defined in the top-level **prefix** dictionary. The dictionary keys are prefix names; the values are dictionaries defining individual prefixes. The prefix values can include **ipv4**, **ipv6**, **pool** and **[allocation](addr-allocation)** attributes.

The **pool** attribute in a prefix can be used when you want a well-defined prefix but don't want to specify IPv4 and IPv6 subnets. The prefix will be allocated from the specified pool on first use.

You can use the names of the *named prefixes* anywhere you would use an IPv4 or IPv6 prefix, for example, as a **links.prefix** value or as a **vlans._vlan_.prefix** value. You can also use them in [custom configuration templates](custom-config-templates.md).

## Example

The following lab topology defines two prefixes. One has a static IPv4 and a static IPv6 subnet and uses the sequential IP address allocation method. The second prefix uses the **lan** pool:

```yaml
prefix:
  s_pfx:
    ipv4: 192.168.42.0/24
    ipv6: 2001:db8:cafe:42::/64
    allocation: sequential
  d_pfx:
    pool: lan
```

You can use the above prefixes to address individual links, for example:

```yaml
nodes: [ r1, r2 ]
links:
- r1:
  prefix: s_pfx
- r2:
  prefix: d_pfx
- r1-r2
```

_netlab_ generates the following link data from the above lab topology (the printout includes only the addressing portion of the link data):

```
- bridge: X_1
  interfaces:
  - ifindex: 1
    ipv4: 192.168.42.1/24
    ipv6: 2001:db8:cafe:42::1/64
    node: r1
  prefix:
    _name: s_pfx
    allocation: sequential
    ipv4: 192.168.42.0/24
    ipv6: 2001:db8:cafe:42::/64
  type: stub
- bridge: X_2
  interfaces:
  - ifindex: 1
    ipv4: 172.16.0.2/24
    node: r2
  prefix:
    _name: d_pfx
    ipv4: 172.16.0.0/24
  type: stub
- interfaces:
  - ifindex: 2
    ipv4: 10.1.0.1/30
    node: r1
  - ifindex: 2
    ipv4: 10.1.0.2/30
    node: r2
  prefix:
    ipv4: 10.1.0.0/30
  type: p2p
```

Finally, you could use named prefixes in a custom configuration template, for example:

```
ip prefix-list stub-4 permit {{ prefix.s_pfx.ipv4 }}
ipv6 prefix-list stub-6 permit {{ prefix.s_pfx.ipv6 }}
```

## Default Prefixes

The [](generic-routing) (when enabled in lab topology) adds default prefixes that can be used in routing filters. You can inspect the default prefixes with the `netlab show defaults prefix` command; the following printout displays the currently defined ones:

```
any:
  ipv4: 0.0.0.0/0
  ipv6: ::/0
```
