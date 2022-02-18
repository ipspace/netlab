# Installing Arista EOS Container

To use Arista EOS with containerlab:

* Download cEOS from Arista Software Download page (registration/login required)
* The downloaded file is a xzipped tar file. If it's saved as .tar file (that's what Chrome on MacOS does), rename it to .tar.xz file
* Unzip the file with `unxz filename`

cEOS tar archive does not contain the container image name (repository and tag); you have to set them when importing the archive into Docker image repository. To display the default cEOS container image name used by *netsim-tools*, run `netlab show images -d eos`. You can use a different tag for your cEOS image (very useful if you want to test different cEOS versions), but then you'll have to specify it in your topology file.

* Install the Docker image with `docker image import <tar-filename> <tag>`, for example `docker image import cEOS64-lab-4.27.2F.tar ceos:4.27.2F`.

If you used a custom container tag, specify it in the topology file, for example:

```
defaults.devices.eos.clab.image: "ceos:4.27.2F"
```

Alternatively, if you want to use the same cEOS image in all your labs, add the following line to `~/topology-defaults.yml` file (replacing `ceos:4.27.2F` with your image tag).

```
devices.eos.clab.image: "ceos.4.27.2F"
```
