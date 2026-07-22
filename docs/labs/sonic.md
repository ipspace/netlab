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
## Using the containerlab Provider (docker-sonic-vs)

Apart from the libvirt Vagrant box above, SONiC can run under **containerlab** using the community
`docker-sonic-vs` image via the `sonic_clab` device (parent: `sonic`). No box build is needed --
supply your own `docker-sonic-vs:latest` image (build it from the
[sonic-buildimage](https://github.com/sonic-net/sonic-buildimage) `docker-sonic-vs` target, or pull a
community build) and select the device:

```
netlab up -d sonic_clab -p clab <topology.yml>
```

`docker-sonic-vs` is a single monolithic container running FRR (`vtysh`); netlab pushes configuration
and runs validation over **docker exec** (the image starts no `sshd`). Native validation therefore
works out of the box -- `netlab up -d sonic_clab <test> --validate` executes the FRR-based `show`
commands over docker-exec. See the [`sonic_clab` caveats](caveats-sonic-clab) for image/connection
details and the verified module set.
