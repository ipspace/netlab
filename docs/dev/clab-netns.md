# Linux Containers and Network Namespaces

Containers provide a relatively new mechanism to execute self-contained network device logic on a host, and *Netlab* supports them through [Containerlab](lab-clab).
From a developer perspective, there are some nuances in dealing with the provisioning of generic Linux containers.

## Network Namespaces

Each container runs inside its own network namespace (`netns`), which contains the logical devices that make up its interfaces to the external world. Containers typically have a minimal number of 1 network interface (not counting the internal loopback); in the context of *Netlab*, most network device containers have multiple interfaces, all of which need to be provisioned.

To minimize dependencies on programs available inside each Linux container image, *Netlab* implements logic to use the Linux host for provisioning while operating inside the target Linux container netns. This logic is triggered by the name of the provisioning script: If the name of the provisioning template ends with `-clab.j2`, it gets executed on the host using `ip netns exec`. Otherwise, a `docker exec` command is used to execute the provisioning script within the container (using whatever program binaries it contains)

See `netsim/ansible/tasks/deploy-config/linux-clab.yml` for details.
