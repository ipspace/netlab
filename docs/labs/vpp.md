(build-vpp)=
# Using a VPP Container

VPP is a [containerlab daemon](platform-daemons) using a locally built **netlab/vpp:latest** image.

* Build the container with `netlab clab build vpp`
* Pin the FD.io release with `netlab clab build vpp --sw-version 25.06-release` (optional; latest release is used by default)
* Use `device: vpp` in the lab topology

The image installs VPP packages from the FD.io Packagecloud repository selected with **defaults.daemons.vpp.clab.repo** (default: `release`).
