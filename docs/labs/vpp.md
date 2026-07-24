(build-vpp)=
# Using a VPP Container

VPP is a [containerlab daemon](platform-daemons) using a locally built **netlab/vpp:latest** image.

* Build the container with `netlab clab build vpp`
* Pin the FD.io release with `netlab clab build vpp --sw-version 25.06-release` (optional; latest release is used by default)
* Use `device: vpp` in the lab topology

VPP nodes default to the **router** role and also support the **bridge** role. They do not support the **host** role.

The image installs VPP packages from the FD.io Packagecloud repository selected with **defaults.daemons.vpp.clab.repo** (default: `release`).

## Control Plane

VPP runs a Linux control-plane daemon in the dataplane network namespace. The default is **bird**; set **control_plane** to **frr** when you need FRRouting (for example IS-IS).

Lab-wide default:

```
defaults.daemons.vpp.control_plane: frr
```

Per-node override:

```
nodes:
  r1:
    device: vpp
    control_plane: frr
```
