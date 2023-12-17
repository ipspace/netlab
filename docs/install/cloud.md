# Running netlab in a Public Cloud

You can run *netlab* on a Ubuntu instance in any public cloud if you want to run containerized versions of network devices (available for Arista EOS, Cumulus Linux, FRR, and Nokia SR Linux). Follow the public cloud installation documentation to create and start an Ubuntu instance, and the [](ubuntu.md) instructions to install *netlab* and other system software.

If you want to run network devices as virtual machines, then the public cloud has to support *nested virtualization*. Create a Ubuntu instance, verify that it has virtualization capabilities (`kvm-ok` is usually a good way to find that out), and follow [](ubuntu.md) instructions.

Nested virtualization seems to be supported on AWS bare-metal instances (they tend to be expensive), Oracle Cloud bare-metal instances, [some Azure instances](https://azure.microsoft.com/en-gb/blog/nested-virtualization-in-azure/), in Google Cloud, by Packet (bare-metal provider) and by Digital Ocean.

## Google Cloud

The following procedure worked for Oswaldo Lamothe who found the trick in [EVE-NG documentation](https://www.eve-ng.net/index.php/documentation/installation/google-cloud-install/) (EVE-NG also needs nested virtualization).

---

GCP does not provide nested virtualization by default. You must begin with setting up a custom image for that purpose from the genuine Ubuntu 20.04 image.
 
I have used the following command for doing so (from the Google Cloud CLI):

```
gcloud compute images create nested-ubuntu-focal \
  --source-image-family=ubuntu-2004-lts \
  --source-image-project=ubuntu-os-cloud \
  --licenses https://www.googleapis.com/compute/v1/projects/vm-options/global/licenses/enable-vmx
```
 
Then, create a new VM with the image you’ve just created (name **nested-ubuntu-focal**).
