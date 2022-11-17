# Whenever You're in Doubt

We had tons of "what should the tool do" discussions when developing the tool. Some of them were distilled into this document.

## The Mission ;)

Every tool should have a Mission, right? Joking aside, _netlab_ tries to streamline virtual (and physical) lab creation. You can also use it to deploy the same functionality (assuming it's supported by the tool) across multiple platforms. If you expect to use it in production or to generate deployable device configurations, you might have to look for another tool.

## New Technologies and Designs

We're always open to new ideas, be it "_we should implement a configuration module for technology X_" or "_we should have ways to configure technology X in a particular way_"... as long as they seem to be applicable to at least several supported devices (and there's a commitment that someone will implement them on those devices) and a wide-enough audience.

Occasionally someone would like to implement a feature or a technology that's available on a single supported device or on a few devices. Showcasing vendor crown jewels is not _netlab_'s primary goal, so we might decide not to implement those ideas in the _netlab_ core. Having said that:

* If you have a new technology that you'd like to implement with _netlab_, feel free to write your own module (example: SRv6).
* If you want an implemented technology to behave in an unusual way, you'll have to create a plugin. We might merge that implementation into the _netlab_ code once it's implemented on enough supported devices -- that's how we got BGP local-as and IBGP-over-EBGP EVPN designs.

Sometimes, we find a wide range of implementations that can be grouped into well-defined smaller clusters. In those cases, we're adding *device features* and use those features in configuration modules to check whether a particular device supports an implementation feature. Examples include:

* Unnumbered IPv4 interfaces
* Running OSPF or IS-IS over unnumbered IPv4 interfaces
* Unnumbered BGP sessions and BGP local-as support
* VLAN implementation differences (switch ports and subinterfaces)
* MPLS protocol support (LDP, BGP-LU, 6PE, VPN)
* First-hop gateway redundancy protocol support

We will not add a *device feature* just because a single device behaves in a peculiar way. In that case, you'll have to deal with [](dev-doubt-suboptimal).

(dev-doubt-suboptimal)=
## Suboptimal Vendor Implementations

_netlab_ is not a perfect multi-vendor deployment tool that would cope with all the differences and caveats of individual implementations. If someone has the need for such a tool, they're most welcome to finance its development, and if someone feels like the _netlab_ implementation for their favorite device should provide that functionality, they're most welcome to implement all the [fixes/quirks](quirks.md) needed to get there _as long as they don't affect netlab core_.

Furthermore, there's no need to dance around suboptimal implementations. It's up to the vendors to get their act together (or not), the most we can do is document the shortcomings in the [caveats](../caveats.md)

Having said that, it's always nice to recognize the documented caveats in [quirks modules](quirks.md) and tell the user why a particular lab won't work, but don't expect that for every documented caveat.
