(build-iosxr-clab)=
# Using Cisco IOS XR Containers

Cisco IOS XRd containers are shipped in two form factors:

* Cisco IOS XRd Control Plane -- a set of processes running on top of the Linux kernel, using the Linux networking stack. *netlab* supports the XRd Control Plane directly, and we test the Cisco IOS XR configuration templates with it.
* Cisco IOS XRd vRouter -- a combination of the control plane and high-performance DPDK dataplane. You can get XRd vRouter to work with *netlab*, but you have to change several node or device defaults.

In both cases, use device `iosxr` with `clab` provider.

```{note}
_netlab_ cannot handle two widely different VM or container implementations of the same device. We could create a different device type for XRd vRouter, but since _netlab_ supports the same functionality on both container variants, it's easier to change the user settings.
```

## Using Cisco IOS XRd Control Plane

* Get the XRd Control Plane container image
* Follow Cisco's documentation to install it ([host setup guide](https://xrdocs.io/virtual-routing/tutorials/2022-08-22-setting-up-host-environment-to-run-xrd)).

## Using Cisco IOS XRd vRouter

*containerlab* runs the Cisco IOS XRd vRouter container inside a micro-VM built with the *vrnetlab* project. Follow the [*containerlab* documentation](https://containerlab.dev/manual/kinds/cisco_xrd_vrouter/) to build that container.

By default, _netlab_ uses `GigabitEthernet0/0/0/N` interface names with Cisco IOS XR. You have to use the `igb` NIC type on the XRd vRouter to get these interface names. Furthermore, *containerlab* uses `Gi0-0-0-N` interface names as link endpoints with the XRd Control Plane, but `Gi0/0/0/N` interface names with the XRd vRouter. Finally, XRd vRouter takes longer to start than the XRd Control Plane, so you have to adjust the "wait for SSH to become ready" timers.

You can change some of these settings with the container environment variables set via `clab.env` node- or device settings. You also have to change the container image, the *containerlab* interface name, the node *kind*, and the *wait for SSH* group variables.

Most of these settings can be changed for individual nodes, but the *containerlab* interface name cannot be. It's thus best to change the [topology defaults](topo-defaults), either in the [lab topology](defaults-topology) or in [user defaults](defaults-user-file) (where you'd omit the `defaults` prefix):

```
defaults.devices.iosxr:
  clab:
    group_vars:
      netlab_check_retries: 100
    image: vrnetlab/cisco_xrd-vrouter:26.2.1
    node:
      env:
        XRD_NIC_TYPE: igb
        CLAB_MGMT_VRF: management
      kind: cisco_xrd_vrouter
    interface:
      name: Gi0/0/0/{ifindex}
```
