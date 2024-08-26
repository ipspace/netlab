(labs-multi-provider)=
# Combining Virtualization Providers

You can use multiple virtualization providers within the same lab topology. One of them is the _primary_ provider specified in the **provider** topology attribute, other(s) are _secondary_ providers specified with **provider** attribute on individual nodes.

```{warning}
You MUST use **[netlab up](../netlab/up.md)** to start the lab and **[netlab down](../netlab/down.md)** to stop the lab when using a combination of virtualization providers. _netlab_ has to do some heavy lifting behind the scenes to make it work.
```

For example, you could have a topology that implements routers as virtual machines (using _libvirt_ primary provider) and end hosts as containers (using _clab_ secondary provider):

```
provider: libvirt

nodes:
  h1:
    device: linux
    provider: clab
  r1:
    device: iosv
    module: [ ospf ]
  r2:
    device: iosv
    module: [ ospf ]
  h2:
    device: linux
    provider: clab

links:
- h1-r1
- r1-r2
- r2-h2
```

_netlab_ supports the following combinations of primary/secondary virtualization providers:

| Primary provider | Secondary provider(s) |
| ---------------- | --------------------- |
| libvirt          |  clab                 |
