# Connecting External Interfaces

I already got questions about connecting *netlab* labs to the outside world. It's trivial to do in an environment using Linux bridges -- connect an external interface to an existing bridge created during **netlab up** process.

The "only" thing to do is to execute an *add to bridge* command during the **netlab up** and *remove from bridge* command during **netlab down**. While there's no need to remove an interface from a bridge that's going to be deleted anyway, one of the parent providers (clab or libvirt) might use permanent bridges, so it's better to be on the safe side.

## Connecting Lab Links to External Interfaces

For the initial implementation we'll assume that the user knows how to create an external interface on Linux (we might add some recipes to the feature documentation) and that she created an interface with a well-defined name (which would make topologies portable across servers with varying Ethernet interface names).

**external.interface** link attribute would be used to connect a *netlab* link with an external interface, for example:

```
nodes: [ r1 ]
links:
- r1: { ipv4: 10.10.10.1/24 }
  external.interface: ext0
```

**Notes:**
* While it's possible to create scenarios where IP addressing between lab devices and external devices _just works_, I'd strongly recommend using static IP addresses.

### Behind the Scenes

* Provider-specific code would have to ensure that the links using external interfaces use Linux bridges. Adding secondary provider to the link should do the trick -- _libvirt_ should work out of the box, _clab_ as the primary provider probably needs extra hacking.
* _external_ provider invoked as a secondary provider would execute `brctl addif _bridge_ _intf_` during **netlab up** process and `brctl delif _bridge_ _intf_` during **netlab down** process. Errors should not be fatal and should be reported as warnings at the end of the lab up/down process.
