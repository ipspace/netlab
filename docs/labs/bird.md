(build-bird)=
# Building BIRD Containers

BIRD containers are not available on public container registries. You must build a local container image with the **[netlab clab build bird](netlab-clab-build)** command before you can use `device: bird` (which only works with `provider: clab`).

You can use the **--version** parameter of the **netlab clab build bird** command to select the BIRD package flavor or a specific release compiled from the source tarball:

| Build command | BIRD version | Installation Method |
|---------------|--------------|---------------------|
| `netlab clab build bird` | CZ.NIC apt repo (v3) | `apt-get install bird3` |
| `netlab clab build bird --version v2` | Ubuntu 24.04 distro package (~2.14) | `apt-get install bird2` |
| `netlab clab build bird --version 3.3.12` | specific BIRD v2 or v3 release | compile from source tarball |

See [](netlab-clab-build) for more details and [](caveats-bird) for BIRD operational caveats.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Default Build (BIRD v3)

Build the default BIRD v3 container shipped with _netlab_:

```
netlab clab build bird
```

This installs the latest BIRD v3 package from CZ.NIC repository on top of the Ubuntu 24.04 image. The default container tag is `netlab/bird:latest` (you can change it with `--tag` parameter).

## Build BIRD v2 Container

Build a BIRD v2 container using the default Ubuntu 24.04 `bird2` package:

```
netlab clab build bird --version v2
```

The default container tag is `netlab/bird:v2`. Use the `--tag` option to get a different container tag, for example:

```
netlab clab build bird --version v2 --tag netlab/bird:latest
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).

## Build Specific BIRD v2/v3 Release from Source

When the **--version** parameter of the **netlab clab build** command is set to a version number, _netlab_ compiles that BIRD release from a source tarball. The Dockerfile template treats **v2** and **v3** as package-based builds; any other value is treated as a source release.

The BIRD source is downloaded from the **defaults.daemons.bird.clab.sw_download_url** URL. The `{sw_version}` in that setting is replaced with the selected release.

The resolved software version is embedded in the rendered Dockerfile. The build command prints `Software version: _version_` before starting the Docker build. Invalid or unavailable versions fail during the Docker build when the source tarball cannot be downloaded. See [BIRD releases](https://bird.nic.cz/download/) for valid version numbers.

When **--version** is specified and **--tag** is omitted, the default tag becomes `netlab/bird:_version_`. For example, the following command builds BIRD 2.17.4 and tags the container as `netlab/bird:2.17.4`

```
netlab clab build bird --version 2.17.4
```

To tag a container built from BIRD sources, use the `--tag` parameter, for example:

```
netlab clab build bird --version 2.17.4 --tag netlab/bird:latest
```

Alternatively, [change the device image](default-device-image) with the **image** [node parameter](node-attributes) or [system defaults](topo-defaults).
