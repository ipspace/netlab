(external-connectivity)=
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

*libvirt* and *containerlab* try to add IPv4 default routes to lab devices. *libvirt* uses a DHCP option, *containerlab* installs a default route into the container network namespace[^DR_EOS]. Most network devices running in a virtual lab are thus able to reach external destinations.

Most box-building recipes for *libvirt* Vagrant boxes recommend using a management VRF for the management interface. The default route is thus installed into the management VRF, and the client you're using on the network device must be VRF-aware to reach external destinations. For example, you'll have to use a command similar to **ping vrf _name_ _destination_** to ping external IP addresses.

[^DR_EOS]: The default route added to the Linux kernel by *containerlab* might not be displayed by the network operating system. For example, if you execute **show ip route** on an Arista EOS container, you won't see a default route, but you'll still be able to reach external destinations.

(external-connectivity-incoming)=
## Connecting to Lab Devices

*libvirt* and *containerlab* [providers](../providers.md) create configuration files that connect all lab devices to a management network. Together with the [default route configured on network devices](external-connectivity-outgoing), it's always possible to reach the management IP address of every device in your lab, but you have to fix the routing in the external network -- the management network IPv4 prefix has to be reachable from the external network.

Alternatively, use *[graphite](../extool/graphite.md)* for GUI-based SSH access to your lab network or port forwarding to map VM/container management TCP ports to the host ports. Port forwarding is always used with [Virtualbox](../labs/virtualbox.md), and configurable with [libvirt](libvirt-port-forwarding) and [containerlab](clab-port-forwarding) providers. Use **netlab report mgmt** to display the host-to-lab-device TCP port mapping.

### Finding the Management IP Addresses

The **netlab report mgmt** command displays the management IP addresses of the lab devices, protocol used to configure the devices (SSH, NETCONF, or Docker), and the username/password used by _netlab_ to configure the device.

Alternatively, you could use Ansible inventory to find the same information:

* Run `ansible-inventory --host _device-name_` to display the Ansible variables for the specified lab device.
* Look for **ansible_host** variable or **ipv4** value in **mgmt** dictionary.

Finally, you could display node information in YAML format with the **[netlab inspect --node _nodename_](../netlab/inspect.md)** command, or analyze the  **nodes** dictionary in the `netlab.snapshot.yml` file with `yq` or a custom script.

(external-ssh-forwarding)=
### Using SSH Port Forwarding

_netlab_ can also create an SSH configuration file that you can add to your `.ssh` directory to access lab devices directly through SSH sessions using the _netlab_ host as a proxy host[^SSHDIY].

After starting the lab, run **netlab report ssh_config** ([more details](netlab-report)) in the lab directory and save the contents into a file in your workstation's `.ssh` directory. Use `Include` directive in the SSH `config` file[^SBF] to give your **ssh** client access to the definitions of lab devices.

[^SSHDIY]: If you're not familiar with SSH configuration files, explore LocalForward, ProxyJump, ProxyCommand, and RemoteCommand OpenSSH [configuration parameters](https://man.openbsd.org/ssh_config).

[^SBF]: At the beginning of the file

You might have to set several [default](topo-defaults) parameters, either in the [user default file](defaults-user-file) or by [using environment variables](defaults-env), to adapt the contents of the SSH configuration to your environment:

* **defaults.ssh.hostname** -- The name under which the _netlab_ server is known on your workstation (default: `netlab`). You have to set this parameter to a hostname that is resolvable on your workstation or combine it with the **defaults.ssh.publicip** parameter, in which case the SSH configuration file will include the definition of the hostname specified in this parameter[^SCTIO].
* **defaults.ssh.publicip** -- The public IP address you can use to reach the _netlab_ server. Use this parameter if you're running the _netlab_ host in an environment where its public IP address might change (for example, in a public cloud).
* **defaults.ssh.netlabpath** -- The `netlab` command path when it's not in the default PATH[^SPLS].

[^SCTIO]: Sounds confusing? Try it out; you cannot do any damage until you save the report results in a file.

[^SPLS]: The SSH process doing proxying on the _netlab_ server is started without executing the shell login script

The **ssh_config** report can also set up SSH port forwarding using the **netlab_ssh_forward** node variable. For example, using the following lab topology, you'd get access to the firewall's HTTPS port (port 443) through the workstation (`localhost`) port 8080 *after establishing an SSH session to the netlab host*.

```
nodes:
  fw:
    netlab_ssh_forward:
    - 8080:443
```

(external-connectivity-control-plane)=
## Control-Plane Connectivity

If you need control-plane connectivity to your lab devices (for example, you'd like to run BGP with a device outside of your lab), consider running your additional devices as virtual machines in the lab. Please see [](platform-unknown) and [](external-unprovisioned-devices) for more details.

To connect *libvirt* virtual machines or *containerlab* containers to the outside world, set [**libvirt.uplink**](libvirt-network-external) or [**clab.uplink**](clab-network-external) link attribute on any link in your topology.

*VirtualBox* uses a different connectivity model. It maps device TCP/UDP ports into host TCP/UDP ports. The default ports mapped for each network device are **ssh**, **http**, and **netconf**. You can add further forwarded ports to the **defaults.providers.virtualbox.forwarded** parameter; the details are beyond the scope of this tutorial.

(external-unprovisioned-devices)=
## Unprovisioned Devices

The easiest way to add network management software (or any third-party workload) to your lab is to deploy it as a node in your network:

* Define an extra **linux** node in your lab topology
* Use the **image** node attribute to specify the node's Vagrant box or container image.

The lab provisioning process will configure the static routes on your VM/container so that it can reach all other devices in your lab.

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

In advanced scenarios connecting your virtual lab with the outside world, you might want to add external devices to your lab topology without managing or provisioning them[^UDC].

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

```{tip}
You still have to specify the device type (either in the node or as the [default device type](default-device-type)) for unmanaged nodes. _netlab_ uses the device type to determine which features a node supports. If you want to use an unsupported unmanaged device, set **‌device** to **‌none**.
```


## Managing Physical Devices

If you want to create configurations for a prewired physical lab, use the [**external** provider](../labs/external.md).

Before using _netlab_ with a physical lab, you must create a lab topology specifying the management IP addresses and interface names for all devices in your lab. Once that's done, save the topology as a blueprint for further lab work.

Starting with the physical lab blueprint topology, add addressing plans (if needed), configuration modules, and configuration module parameters. Use **netlab up** to start the data transformation and configuration deployment on physical devices.

Please note that _netlab_ does not contain a cleanup procedure for physical devices -- you'll have to remove the device configurations before starting the next lab.