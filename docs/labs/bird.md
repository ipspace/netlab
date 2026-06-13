(build-bird)=
# Building BIRD Containers

BIRD containers are not available on public container registries. You must build a local container image before using `provider: clab` with `device: bird`.

_netlab_ ships three Docker build targets for BIRD (use **netlab clab build --list** to display them):

| Target | Default image tag | BIRD version | Method |
|--------|-------------------|--------------|--------|
| `bird` | `netlab/bird:latest` | Ubuntu 24.04 distro package (~2.14) | `apt install bird2` |
| `bird.v3` | `netlab/bird.v3:latest` | CZNIC apt repo (v3) | pre-built packages |
| `bird.v2_from_src` | `netlab/bird.v2_from_src:latest` | configurable (default 2.19.1) | compile from source tarball |

See [](netlab-clab-build) for more details and [](caveats-bird) for BIRD operational caveats.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Default Build (apt-based BIRD v2)

Build the default BIRD v2 container shipped with _netlab_:

```
netlab clab build bird
```

This installs the BIRD version provided by the Ubuntu 24.04 package repository (~2.14 at the time of this writing).

## Build BIRD v3 Container

Build a BIRD v3 container from the CZNIC package repository:

```
netlab clab build bird.v3
```

To use the v3 build as the default BIRD image expected by lab topologies, use the `--tag` option.

```
netlab clab build bird.v3 --tag netlab/bird:latest
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).

## Build Specific BIRD v2 Release from Source

The **bird.v2_from_src** target compiles BIRD v2 from a source tarball. _netlab_ renders `Dockerfile.v2_from_src.j2` with system defaults before starting the Docker build.

The BIRD release is taken from (in order of precedence):

* The **--sw-version** CLI parameter
* **defaults.daemons.bird.clab.sw_version** (currently 2.19.1)

The BIRD source is downloaded from the **defaults.daemons.bird.clab.sw_download_url** URL. The `{sw_version}` in that setting is replaced with the selected release.

The resolved software version is embedded in the rendered Dockerfile. The build command prints `Software version: _version_` before starting the Docker build. Invalid or unavailable versions fail during the Docker build when the source tarball cannot be downloaded. See [BIRD releases](https://bird.nic.cz/download/) for valid version numbers.

The default container tag is `netlab/bird.v2_from_src:latest`. When **--sw-version** is specified and **--tag** is omitted, the default tag becomes `netlab/bird.v2_from_src:_version_`. For example, the following command builds BIRD 2.17.4 and tags the container as `netlab/bird.v2_from_src:2.17.4`

```
netlab clab build bird.v2_from_src --sw-version 2.17.4
```

Use the `netlab/bird:latest` tag to install a from-source build as the default BIRD image:

```
netlab clab build bird.v2_from_src --tag netlab/bird:latest
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).
