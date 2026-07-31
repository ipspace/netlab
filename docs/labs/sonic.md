(build-sonic)=
# Building a Sonic Vagrant Libvirt Box

You can use the **netlab libvirt package** command to build a Sonic Vagrant box for a Sonic virtual machine:

* Download the **sonic-vs.img.gz** image from Azure or [sonic.software](https://sonic.software/) into an empty directory.
* Unzip image with **gunzip _gz-file-name_**.
* Execute **netlab libvirt package sonic _img-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process, you might have to disable ZTP or clean up the initial configuration database. The **netlab libvirt config sonic** command displays the build recipe:

```{eval-rst}
.. include:: sonic.txt
   :literal:
```

(labs-sonic-clab)=
## Using the SoNIC containers

SONiC also runs under *containerlab* using the community `docker-sonic-vs` image. There is no box
to build -- select the `clab` provider:

```
netlab up -d sonic -p clab <topology.yml>
```

### Getting the container image

*netlab* does not ship or distribute `docker-sonic-vs`; you supply it yourself. It is published as
a build artefact of the [sonic-buildimage](https://github.com/sonic-net/sonic-buildimage) project
rather than on a public registry, so you either download a build or make one:

* **Download a published build.** The image is published as an artefact of the SONiC Azure build
  pipelines. From <https://sonic-build.azurewebsites.net/ui/sonic/pipelines>:

  * scroll to the bottom of the pipeline list, where the **vs** platform is listed;
  * pick a branch (for example `202405`) and open **Build History**;
  * choose the latest build whose *Result* is successful and open **Artifacts**;
  * open the artifact, scroll to **target/docker-sonic-vs.gz**, and download it.

  *containerlab* documents the same path for its
  [`sonic-vs` kind](https://containerlab.dev/manual/kinds/sonic-vs/), which uses this image.
  [sonic.software](https://sonic.software/) is an unofficial index that is sometimes offered as an
  alternative, but it carries SONiC *installation* images (`sonic-vs.img`, used for the Vagrant box
  above) rather than the container artefact.

  Then load it:

  ```
  gunzip docker-sonic-vs.gz
  docker load -i docker-sonic-vs
  ```

  Check the tag `docker load` restored with **docker images**; retag it to
  `docker-sonic-vs:latest` if it differs.

* **Build it yourself** from `sonic-buildimage`:

  ```
  git clone --recurse-submodules https://github.com/sonic-net/sonic-buildimage.git
  cd sonic-buildimage
  make init
  make configure PLATFORM=vs
  make target/docker-sonic-vs.gz
  docker load -i target/docker-sonic-vs.gz
  ```

The device definition expects the image to be tagged **`docker-sonic-vs:latest`**; override
`clab.image` in your topology if yours is tagged differently. This submission was tested with
`docker-sonic-vs:latest`.

### How it works

`docker-sonic-vs` is a single monolithic container running FRR (`vtysh`), unlike the VM above which
runs FRR in a nested `bgp` container. *netlab* pushes configuration and runs validation over
**docker exec** -- the image starts no `sshd`. The device inherits the `frr` device, so the FRR
control-plane templates are used directly and only the container-specific parts
(`<module>/sonic-clab.j2`) are SONiC's own.

See the [SONiC caveats](caveats-sonic-clab) for what is and is not supported.
