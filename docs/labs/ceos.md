# Installing Arista EOS Container

To use Arista EOS with containerlab you need to register for a free account on [Arista's website](https://www.arista.com/en/login).  You then have 2 options to download the EOS container.

## Option 1: Download the container from Arista's website


The image is a tar archive that contains the EOS image and a license file. You will need to extract the EOS image from the archive and place it in the `images` directory of containerlab.

* Download cEOS from [Arista Software Download page](https://www.arista.com/en/support/software-download) (registration/login required)
* The downloaded file is a xzipped tar file. If it's saved as .tar file (that's what Chrome on MacOS does), rename it to .tar.xz file
* Unzip the file with `unxz filename`

cEOS tar archive does not contain the container image name (repository and tag); you have to set them when importing the archive into Docker image repository. To display the default cEOS container image name used by *netlab*, run `netlab show images -d eos`. You can use a different tag for your cEOS image (very useful if you want to test different cEOS versions), but then you'll have to specify it in your topology file.

* Install the Docker image with `docker image import <tar-filename> <tag>`, for example `docker image import cEOS64-lab-4.27.2F.tar ceos:4.27.2F`.

If you used a custom container tag, specify it in the topology file, for example:

```
defaults.devices.eos.clab.image: "ceos:4.27.2F"
```

Alternatively, if you want to use the same cEOS image in all your labs, add the following line to `~/.netlab.yml` file (replacing `ceos:4.27.2F` with your image tag).

```
devices.eos.clab.image: "ceos.4.27.2F"
```

## Option 2: Download the container using eos-downloader

See the [eos-downloader documentation](https://pypi.org/project/eos-downloader/) for details.

Go to [the user portal page](https://www.arista.com/en/users/profile) and create a portal token to generate and record your token.

Install eos-downloader:

```bash
pip install eos-downloader
```

Follow the instructions via the [eos-downloader documentation](https://pypi.org/project/eos-downloader/).
