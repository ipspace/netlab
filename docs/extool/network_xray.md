(extool-network_xray)=
# network-xray

[network-xray](https://github.com/rclab-dev/network-xray) displays a lab topology and routing state collected from FRRouting and Nokia SR Linux containers.

```{warning}
network-xray receives the Docker socket, which provides control over the host's Docker daemon and is effectively root access on a typical lab host. Its web interface listens on all host interfaces and has no login. Use it only on a trusted lab host and restrict access to the published port.
```

Add the following lines to a lab topology file to use network-xray with _netlab_:

```
tools:
  network_xray:
```

The URL is printed during **netlab up**. Use **netlab connect network_xray** to display it again. The web port is 8600, or 8600 plus the lab instance ID when using the [multilab plugin](plugin-multilab).

**Notes:**

* network-xray works only with containerlab-only topologies and expects the default `clab-<lab>-<node>` container names (a custom `prefix` is not supported).
* network-xray only reads the router state through Docker (`vtysh -c 'show ...'` on FRR, `sr_cli 'info from state ...'` on SR Linux); it does not change the router configuration. The lab directory is mounted read-only.
* Router-state collection supports FRR and SR Linux, with limits on supported features and topology layouts. Other devices can appear in the topology without router-state details. _netlab_ does not check whether network-xray supports all the devices used in the lab topology.
* Only nodes connected by two-endpoint links are collected. SR Linux collection uses the default network instance and IPv4 unicast routes.
* This tool definition does not export validation data or integrate **netlab validate** results.
* The network-xray container is stopped and removed when the lab is shut down with **netlab down**.
