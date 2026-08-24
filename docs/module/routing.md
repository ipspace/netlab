(generic-routing)=
# Generic Routing Configuration Module

This configuration module implements generic routing features:

* [Routing policies (route maps)](generic-routing-policies)
* [Prefix filters (prefix-lists)](generic-routing-prefixes)
* [BGP AS-path filters](generic-routing-aspath)
* [BGP community filters](generic-routing-community)
* [Static routes](generic-routing-static)
* [Access control lists](generic-routing-acl)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(generic-routing-platforms)=
## Platform Support

These platforms support generic routing features:

```{features}
- title: Routing<br>policies
  enabled: routing.policy
- title: Static<br>routes
  enabled: routing.static
  caveats: routing.static.caveats
- title: IPv4/IPv6<br>ACL
  enabled: routing.acl
```

You can use these objects in routing policies (on platforms that support them):

```{features}
- title: Prefix<br>filters
  enabled: routing.prefix
  caveats: routing.prefix.caveats
- title: AS-path<br>filters
  enabled: routing.aspath
  caveats: routing.aspath.caveats
- title: BGP community<br>lists
  enabled: routing.community
  caveats: routing.community.caveats
```

```{tip}
See [Routing Integration Tests Results](https://release.netlab.tools/_html/coverage.routing) for more details.
```

```{include} routing-policy.txt
```
```{include} routing-prefix.txt
```
```{include} routing-aspath.txt
```
```{include} routing-clist.txt
```
```{include} routing-static.txt
```
```{include} routing-acl.txt
```
```{include} routing-advanced.txt
```
