(build-bird)=
# Building BIRD Containers

BIRD containers are not available on public container registries. You must build a local container image before using `provider: clab` with `device: bird`.

_netlab_ ships one Docker build target for BIRD (use **netlab clab build --list** to display it). Use the **--sw-version** parameter to select the BIRD package flavor or a specific source release:

| Build command | BIRD version | Method |
|---------------|--------------|--------|
| `netlab clab build bird` | Ubuntu 24.04 distro package (~2.14) | `apt install bird2` |
| `netlab clab build bird --sw-version bird3` | CZNIC apt repo (v3) | pre-built packages |
| `netlab clab build bird --sw-version 2.17.4` | specific BIRD v2 release | compile from source tarball |

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
netlab clab build bird --sw-version bird3
```

To use a different tag for the v3 build, use the `--tag` option.

```
netlab clab build bird --sw-version bird3 --tag netlab/bird:v3
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).

## Build Specific BIRD v2 Release from Source

When **--sw-version** is set to a version number, _netlab_ compiles that BIRD v2 release from a source tarball. The Dockerfile template treats **bird2** and **bird3** as package-based builds; any other value is treated as a source release.

The BIRD release is taken from (in order of precedence):

* The **--sw-version** CLI parameter

The BIRD source is downloaded from the **defaults.daemons.bird.clab.sw_download_url** URL. The `{sw_version}` in that setting is replaced with the selected release.

The resolved software version is embedded in the rendered Dockerfile. The build command prints `Software version: _version_` before starting the Docker build. Invalid or unavailable versions fail during the Docker build when the source tarball cannot be downloaded. See [BIRD releases](https://bird.nic.cz/download/) for valid version numbers.

When **--sw-version** is specified and **--tag** is omitted, the default tag becomes `netlab/bird:_version_`. For example, the following command builds BIRD 2.17.4 and tags the container as `netlab/bird:2.17.4`

```
netlab clab build bird --sw-version 2.17.4
```

Use the `netlab/bird:latest` tag to install a from-source build as the default BIRD image:

```
netlab clab build bird --sw-version 2.17.4 --tag netlab/bird:latest
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).
