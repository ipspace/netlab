(netlab-test)=
# Test Virtual Lab Installation

**netlab test** libvirt- or containerlab-based virtual lab installation. It creates a simple virtual lab using Linux VMs or FRR containers, starts the lab, deploys initial configurations, destroys the lab, and cleans up.

## Usage

```text
usage: netlab test [-h] [-w WORKDIR] [-v] {clab,grpc,libvirt,podman}

Test virtual lab installation

positional arguments:
  {clab,grpc,libvirt,podman}
                        Run tests for the specified provider/environment

options:
  -h, --help            show this help message and exit
  -w WORKDIR, --work-directory WORKDIR
                        Working directory (default: test)
  -v, --verbose         Verbose logging
```

You can execute these tests:

| Name | Tests |
|------|---------------|
| clab | Docker and containerlab using FRR Docker containers |
| grpc | Docker, containerlab, and gRPC libraries using SR Linux Docker containers |
| libvirt | Vagrant and libvirt using Linux virtual machines |
| podman | Podman and containerlab using FRR podman containers |

## Testing Procedure

**netlab test** command:

* Checks whether the selected virtualization provider is installed;
* Creates a working directory and copies the sample lab topology containing three routers and a few links into that directory;
* Executes **netlab up** to create configuration files, start the lab, and configure network devices.
* Destroys the lab with **netlab down**
* Cleans up the working directory
