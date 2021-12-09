# Platform Caveats

## Cumulus Linux in ContainerLab

* *containerlab* could run Cumulus Linux as a container or as a micro-VM with *firecracker* (default, requires KVM). To run Cumulus VX as a pure container, add **runtime: docker** parameter to node data.
* *netsim-tools* uses Cumulus VX containers created by Michael Kashin and downloaded from his Docker Hub account. Once Nvidia releases an official container image, change the container name with **defaults.providers.clab.devices.cumulus.image.clab** parameter (or by editing the `topology-defaults.yml` file included with *netsim-tools*).

## Fortinet FortiOS

* *FortiOS* VM images by default have a 15 day evaluation license. The VM has [limited capabilities](https://docs.fortinet.com/document/fortigate-private-cloud/6.0.0/fortigate-vm-on-kvm/504166/fortigate-vm-virtual-appliance-evaluation-license) without a license file. It will work for 15 days from first boot, at which point you must install a license file or recreate the vagrant box completely from scratch.
* Ansible automation of FortiOS requires the installation of the [FortiOS Ansible Collection 2.1.3 or greater](https://galaxy.ansible.com/fortinet/fortios) and a FortiOS version > 6.0.
* Ansible configuration of OSPF is currently broken due to a [suspected bug](https://github.com/fortinet-ansible-dev/ansible-galaxy-fortios-collection/issues/150) in the FortiOS Ansible Collection. To work around this issue, you must manually configure a OSPF network statement by logging in to the device after initial provisioning. For example:

```bash
vagrant ssh fw
config router ospf
config network
edit 1
set area 0.0.0.1
set prefix 0.0.0.0/0
end
end
```

## FRR

* *containerlab* FRR containers run FRR release 7.5.0 -- the latest release that survives FRR daemon restart during the initial configuration process.
* *netsim-tools* don't support FRR running in a Linux VM. Use Cumulus Linux instead.

## Generic Linux

*Generic Linux device* is a Linux VM running Ubuntu 20.04 or an Alpine/Python container. To use any other Linux distribution, add **image** attribute with the name of Vagrant box or Docker container to the node data[^1]; the only requirements are working Python environment (to support Ansible playbooks used in **netlab initial** command) and the presence of **ip** command used in initial device configuration.

[^1]: You can also set the **defaults.devices.linux.image._provider_** attribute to change the Vagrant box for all Linux hosts in your lab.

### Host Routing

Generic Linux device is an IP host that does not support IP forwarding or IP routing protocols. It uses static routes set up as follows:

* IPv4 default route points to Vagrant management interface (set by Vagrant/DHCP).
* IPv6 default route points to whichever adjacent device is sending IPv6 Route Advertisement messages (default Linux behavior).
* IPv4 static routes for all IPv4 address pools defined in lab topology point to the first neighbor on the first non-management interface.

**Corollary:** Linux devices SHOULD have a single P2P link to an adjacent network device. If you encounter problems using any other lab topology, please submit a Pull Request fixing it instead of complaining ;)

### LLDP

* LLDP on Generic Linux is started in Ubuntu VMs but not in Alpine containers.

## Mikrotik CHR RouterOS

* LLDP on Mikrotik CHR RouterOS is enabled on all the interfaces.
