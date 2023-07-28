# External Connectivity

_netlab_ contains several mechanisms that allow you to manage physical labs, add physical devices to virtual labs, connect to the outside world from virtual lab devices, or use network management software packaged as containers or virtual machines with your virtual labs.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(external-connectivity-outgoing)=
## Outbound Connectivity

*libvirt*, *VirtualBox* and *containerlab* try to add IPv4 default routes to lab devices. *libvirt* and *Virtualbox* use a DHCP option, *containerlab* installs a default route into the container network namespace[^DR_EOS]. Most network devices running in a virtual lab are thus able to reach external destinations.

Most box-building recipes for *libvirt* and *Virtualbox* Vagrant plugins recommend using a management VRF for the management interface. The default route is thus installed into the management VRF, and the client you're using on the network device has to be VRF-aware to reach external destinations. For example, you'll have to use a command similar to **ping vrf _name_ _destination_** to ping external IP addresses.

[^DR_EOS]: The default route added to Linux kernel by *containerlab* might not be displayed by the network operating system. For example, if you execute **show ip route** on an Arista EOS container, you won't see a default route, but you'll still be able to reach external destinations.

(external-connectivity-incoming)=
## Connecting to Lab Devices

*libvirt* and *containerlab* [providers](../providers.md) create configuration files that connect all lab devices to a management network. Together with the [default route configured on network devices](external-connectivity-outgoing), it's always possible to reach the management IP address of every device in your lab, but you have to fix the routing in the external network -- the management network IPv4 prefix has to be reachable from the external network.

Alternatively, use *[graphite](../extool/graphite.md)* for GUI-based SSH access to your lab network.

### Finding the Management IP Addresses

You could use Ansible inventory to find the management IP addresses[^VBS]:

* Run `ansible-inventory --host _device-name_` to display the Ansible variables for the specified lab device.
* Look for **ansible_host** variable or **ipv4** value in **mgmt** dictionary.

You could also [create an inventory of all lab devices in a single YAML](../outputs/devices.md) file with `netlab create -o devices`. The resulting file (default: `netlab-devices.yml`) contains a dictionary of all lab devices. Use the dictionary value for a lab device like you would use the results of `ansible-inventory` command.

[^VBS]: And SSH ports if you're using *Virtualbox*.

(external-connectivity-control-plane)=
## Control-Plane Connectivity

If you need control-plane connectivity to your lab devices (for example, you'd like to run BGP with a device outside of your lab), consider running your additional devices as virtual machines in the lab. Please see [](platform-unknown) and [](external-unprovisioned-devices) for more details.

To connect *libvirt* virtual machines or *containerlab* containers to the outside world, set [**libvirt.uplink**](libvirt-network-external) or [**clab.uplink**](clab-network-external) link attribute on any link in your topology.

*VirtualBox* uses a different connectivity model. It maps device TCP/UDP ports into host TCP/UDP ports. The default ports mapped for each network device are **ssh**, **http** and **netconf**. It's possible to add additional forwarded ports to the **defaults.providers.virtualbox.forwarded** parameter; the details are beyond the scope of this tutorial.

*VirtualBox* can connect VMs to the external world. That capability is not part of _netlab_ functionality; please feel free to [submit a Pull Request](../dev/guidelines.md) implementing it.

(external-unprovisioned-devices)=
## Unprovisioned Devices

The easiest way to add network management software (or any third-party workload) to your lab is to deploy it as a node in your network:

* Define an extra **linux** node in your lab topology
* Use **image** node attribute to specify a Vagrant box or container image to use.

The lab provisioning process will configure the static routes on your VM/container to allow it to reach all other devices in your lab.

The VM device provisioning process will fail if your VM does not contain Python (used by Ansible) or the necessary Linux CLI commands (example: **ip** to add static routes); container interface addresses and routing tables are [configured from the Linux server](clab-linux).

If you want to use a VM that cannot be configured as a Linux host, put that node into the [**unprovisioned** group](group-special-names), for example:

```
---
defaults.device: iosv
  
nodes:
  r1:
  r2:
  nms:
    device: linux
    image: awesome-sw

groups:
  unprovisioned:
    members: [ nms ]
```

```{warning}
Devices in the **unprovisioned** group will not get IP addresses on interfaces other than the management interface, or static routes to the rest of the network.

As they are still connected to the management network, they can always reach the management interfaces of all network devices.
```

(external-unmanaged)=
## Unmanaged Devices

In advanced scenarios connecting your virtual lab with the outside world, you might want to include external devices into your lab topology without managing or provisioning them[^UDC].

[^UDC]: Assuming you connected one or more Linux bridges in your lab with the outside world.

For example, if you want to have a BGP session with an external router:

* Define the external router as another device in your lab topology.
* Use static IP prefixes on the link between the virtual devices and the external router to ensure the virtual devices get IP addresses from the subnet configured on the external router
* Define BGP AS numbers used by your devices and the external router -- _netlab_ will automatically build IBGP/EBGP sessions between lab devices and the external device
* Use [**unmanaged** node attribute](node-attributes) on the external node to tell _netlab_ not to include it in Ansible inventory or Vagrant/containerlab configuration files

Here is the resulting topology file using an Arista vEOS VM running BGP with an external Arista EOS switch. The lab is  using *libvirt* public network to connect the VM to the outside world:

```
defaults.device: eos
module: [ bgp ]
nodes:
  vm:
    bgp.as: 65000
  sw:
    unmanaged: True
    bgp.as: 65001
links:
- vm:
    ipv4: 10.42.0.2/24
  sw:
    ipv4: 10.42.0.1/24
  libvirt.public: True
```

## Managing Physical Devices

If you want to create configurations for a prewired physical lab, use the [**external** provider](../labs/external.md).

Before using _netlab_ with a physical lab, you'll have to create a lab topology that specifies the specify management IP addresses and interface names for all devices in your lab. Once that's done, save the topology as a blueprint for further lab work.

Starting with the physical lab blueprint topology, add addressing plans (if needed), configuration modules, and configuration module parameters. Use **netlab up** to start the data transformation process and configuration deployment on physical devices.

Please note that _netlab_ does not contain a cleanup procedure for physical devices -- you'll have to remove the device configurations before starting the next lab.