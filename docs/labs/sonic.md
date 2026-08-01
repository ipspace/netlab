(build-sonic)=
# Preparing a SONiC Box or Container

_netlab_ supports SONiC running in a VM or in a container. Unfortunately, there's no ready-to-use Vagrant box or Docker container that you could pull down from a public registry; you have to [build the box](build-sonic-box) or [download and install the container](build-sonic-container) manually.

(build-sonic-box)=
## Building a SONiC Vagrant Box

You can use the **netlab libvirt package** command to build a SONiC Vagrant box for a SONiC virtual machine:

* Download the **sonic-vs.img.gz** image from Azure or [SONiC.software](https://SONiC.software/) into an empty directory.
* Unzip image with **gunzip _gz-file-name_**.
* Execute **netlab libvirt package sonic _img-file-name_** and follow the instructions

```{warning}
If you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

### Initial Device Configuration

During the box-building process, you might have to disable ZTP or clean up the initial configuration database. The **netlab libvirt config sonic** command displays the build recipe:

```{eval-rst}
.. include:: sonic.txt
   :literal:
```

(build-sonic-container)=
## Downloading and Installing SONiC containers

SONiC also runs under *containerlab* using the community `docker-sonic-vs` container. The container is published as
a build artifact of the [sonic-buildimage](https://github.com/sonic-net/sonic-buildimage) project, so you either download a build or make one.

### Download a Published Build

The SONiC container image is published as an artifact of the SONiC Azure build pipelines. From <https://sonic-build.azurewebsites.net/ui/sonic/pipelines>:

* Scroll to the bottom of the pipeline list, where the **vs** platform is listed;
* Pick a branch (for example `202405`) and open **Build History**;
* Choose the latest build whose *Result* is successful and open **Artifacts**;
* Open the artifact, scroll to **target/docker-sonic-vs.gz**, and download it.

*containerlab* documents the same path for its
[`sonic-vs` kind](https://containerlab.dev/manual/kinds/sonic-vs/), which uses this image. [sonic.software](https://SONiC.software/) is an unofficial index that is sometimes offered as an alternative, but it carries SONiC *installation* images (`sonic-vs.img`, used for the Vagrant box
above) rather than the container artifact.

After downloading the container, unpack and load it:

```
gunzip docker-sonic-vs.gz
docker load -i docker-sonic-vs
```

Check the tag `docker load` restored with **docker images**; retag it to `docker-sonic-vs:latest` if necessary.

### Build a SONiC Container

Use this process in an empty directory to build a SONiC container from the `sonic-buildimage` repository:

```
git clone --recurse-submodules https://github.com/sonic-net/sonic-buildimage.git
cd sonic-buildimage
make init
make configure PLATFORM=vs
make target/docker-sonic-vs.gz
docker load -i target/docker-sonic-vs.gz
```

The device definition expects the image to be tagged **`docker-sonic-vs:latest`**; override
`defaults.devices.sonic.clab.image` in your topology if yours is tagged differently.

### How SONiC Container Works

`docker-sonic-vs` is a single monolithic container running FRR (`vtysh`) (unlike the VM, which runs FRR in a nested `bgp` container). The container does not start the SSH daemon; *netlab* pushes device configuration and runs validation with **docker exec** commands.

The device inherits from the `frr` device and uses FRR control-plane configuration templates.

See the [SONiC caveats](caveats-sonic-clab) for what is and is not supported.
