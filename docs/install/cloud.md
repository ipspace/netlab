(install-cloud)=
# Running netlab in a Public Cloud

You can run *netlab* on an Ubuntu instance in any public cloud if you want to run containerized versions of network devices (available for Arista EOS, Cumulus Linux, FRR, and Nokia SR Linux). Follow the public cloud installation documentation to create and start an Ubuntu instance, and the [](install-ubuntu) instructions to install *netlab* and other system software.

If you want to run network devices as virtual machines, the public cloud has to support *nested virtualization*. Create an Ubuntu instance, verify its virtualization capabilities (a good way to check is with `kvm-ok`), and follow the [](install-ubuntu) instructions.

Nested virtualization is supported on [some AWS EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html), AWS [bare-metal instances](https://aws.amazon.com/blogs/aws/new-amazon-ec2-bare-metal-instances-with-direct-access-to-hardware/) (they tend to be expensive), Oracle Cloud bare-metal instances, [some Azure instances](https://azure.microsoft.com/en-gb/blog/nested-virtualization-in-azure/), in Google Cloud, by Packet (bare-metal provider), and by DigitalOcean.

## Google Cloud

Google Cloud [supports nested virtualization](https://cloud.google.com/compute/docs/instances/nested-virtualization/overview), which you can enable with either the Google Cloud CLI or the REST API. Google Cloud documentation [recommends using the Google Cloud CLI](https://cloud.google.com/compute/docs/instances/nested-virtualization/enabling) to create a VM with nested virtualization enabled [^GCNV].

[^GCNV]: See [comments by Aleksey Popov](https://github.com/ipspace/netlab/discussions/2554) for more details.
 
The `enable_nested_virtualization` parameter is also [supported by the Terraform Google provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance#nested_advanced_machine_features).
