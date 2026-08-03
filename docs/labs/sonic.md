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
* Pick a branch -- the newest release branch (for example `202605`) or `master` -- and open **Build History**;
* Choose the latest build whose *Result* is **succeeded** and open **Artifacts**. Builds that
  were *canceled* are listed alongside the successful ones, and they have an **Artifacts** link
  too;
* Open the artifact (there is only one, `sonic-buildimage.vs`) and find **target/docker-sonic-vs.gz**
  in the file list. Take care not to pick **target/docker-sonic-vs-asan.gz**, which sits next to
  it -- that is an AddressSanitizer build.

The file list is long; if you would rather not scroll it, the download URL can be built by hand
once you know the branch and the build ID from the *Build History* page:

```
https://sonic-build.azurewebsites.net/api/sonic/artifacts?branchName=202605&platform=vs&buildId=1166687&target=target%2Fdocker-sonic-vs.gz
```

After downloading the container, unpack and load it:

```
gunzip docker-sonic-vs.gz
docker load -i docker-sonic-vs
```

The archive carries the tag `docker-sonic-vs:latest`, which is what the device definition
expects, so there is usually nothing to retag.

```{warning}
**docker load** replaces any existing `docker-sonic-vs:latest` image -- it prints
`The image docker-sonic-vs:latest already exists, renaming the old one with ID ... to empty string`
and leaves the previous image untagged. If you want to keep the image you already have, tag it
first (for example `docker tag docker-sonic-vs:latest docker-sonic-vs:previous`) and select
between them with `defaults.devices.sonic.clab.image`.
```

You can check which build you got with:

```
docker run --rm --entrypoint cat docker-sonic-vs:latest /etc/sonic/sonic_version.yml
```

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
