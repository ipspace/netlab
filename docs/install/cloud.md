# Running netlab in a Public Cloud

You can run *netlab* on a Ubuntu instance in any public cloud if you want to run containerized versions of network devices (available for Arista EOS, Cumulus Linux, FRR, and Nokia SR Linux). Follow the public cloud installation documentation to create and start an Ubuntu instance, and the [](ubuntu.md) instructions to install *netlab* and other system software.

If you want to run network devices as virtual machines, the public cloud has to support *nested virtualization*. Create a Ubuntu instance, verify that it has virtualization capabilities (`kvm-ok` is usually a good way to find that out), and follow [](ubuntu.md) instructions.

Nested virtualization seems to be supported on AWS bare-metal instances (they tend to be expensive), Oracle Cloud bare-metal instances, [some Azure instances](https://azure.microsoft.com/en-gb/blog/nested-virtualization-in-azure/), in Google Cloud, by Packet (bare-metal provider), and by Digital Ocean.

## Google Cloud

Google Cloud [supports nested virtualization](https://cloud.google.com/compute/docs/instances/nested-virtualization/overview) that can be enabled with either Google Cloud CLI or REST API. Google Cloud documentation [recommends using the Google Cloud CLI](https://cloud.google.com/compute/docs/instances/nested-virtualization/enabling) to create a VM with enabled nested virtualization[^GCNV].

[^GCNV]: See [comments by Aleksey Popov](https://github.com/ipspace/netlab/discussions/2554) for more details.
 
The `enable_nested_virtualization` parameter is also [supported by the Terraform Google provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance#nested_advanced_machine_features).

Alternatively, you could use the following (now obsolete) procedure to create a custom image with enabled nested virtualization (found by Oswaldo Lamothe in the [EVE-NG documentation](https://www.eve-ng.net/index.php/documentation/installation/google-cloud-install/)).

---

GCP does not provide nested virtualization by default. You must begin by setting up a custom image for that purpose from the genuine Ubuntu image.
 
I have used the following command for doing so (from the Google Cloud CLI):

```
gcloud compute images create nested-ubuntu-focal \
  --source-image-family=ubuntu-2004-lts \
  --source-image-project=ubuntu-os-cloud \
  --licenses https://www.googleapis.com/compute/v1/projects/vm-options/global/licenses/enable-vmx
```
 
Then, create a new VM with the image you’ve just created (name **nested-ubuntu-focal**).
