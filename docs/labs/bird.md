(build-bird)=
# Building BIRD Containers

BIRD containers are not available on public container registries. You must build a local container image before using `provider: clab` with `device: bird`.

_netlab_ ships three Docker build targets for BIRD (use **netlab clab build --list** to display them):

| Target | Default image tag | BIRD version | Method |
|--------|-------------------|--------------|--------|
| `bird` | `netlab/bird:latest` | Ubuntu 24.04 distro package (~2.14) | `apt install bird2` |
| `bird.v3` | `netlab/bird.v3:latest` | CZNIC apt repo (v3) | pre-built packages |
| `bird.v2_from_src` | `netlab/bird.v2_from_src:2.19.1` | configurable (default 2.19.1) | compile from source tarball |

See [](lab-clab) for generic **netlab clab build** usage and [](caveats-bird) for BIRD operational caveats.

## Default Build (apt-based v2)

Build the default BIRD v2 container shipped with _netlab_:

```
netlab clab build bird
```

This installs the BIRD version provided by the Ubuntu 24.04 package repository (~2.14 at the time of this writing).

## BIRD v3

Build a BIRD v3 container from the CZNIC package repository:

```
netlab clab build bird.v3
```

To use the v3 build as the default BIRD image expected by lab topologies:

```
netlab clab build bird.v3 --tag netlab/bird:latest
```

## Build from Source (v2, specific release)

The **bird.v2_from_src** target compiles BIRD v2 from a source tarball. The default release comes from **defaults.daemons.bird.clab.sw_version** (currently 2.19.1). Override it with the **SW_VERSION** environment variable.

The resolved version is passed to the Docker build as **SW_VERSION** and used as the default container tag.

```
netlab clab build bird.v2_from_src
SW_VERSION=2.17.4 netlab clab build bird.v2_from_src
```

To install a from-source build as the default BIRD image:

```
netlab clab build bird.v2_from_src --tag netlab/bird:latest
```

Invalid or unavailable versions fail before the Docker build starts with a message naming the version and download URL. See [BIRD releases](https://bird.nic.cz/download/) for valid version numbers.

## Using a Custom Image in a Lab Topology

You can select a non-default container image with the **image** [node parameter](node-attributes) or change the system default with **defaults.daemons.bird.clab.image** ([more details](topo-defaults)).
