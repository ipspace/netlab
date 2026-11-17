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
* By default, this tool definition does not export validation data. See [Validation Results](extool-network_xray-validate) to make **netlab validate** results available to network-xray.
* The network-xray container is stopped and removed when the lab is shut down with **netlab down**.

(extool-network_xray-validate)=
## Validation Results

The **tools.network_xray** plugin (loaded with the tool) can run **[netlab validate](../netlab/validate.md) --format json** in the lab directory while the lab is running and write the results into `network_xray/validate.json`, where network-xray can read them through the read-only lab directory mount.

The validation loop is disabled by default. Enable it with:

```
tools:
  network_xray:
    validate: True
```

* The background process is started after the tools have been started by **netlab up** and stopped by **netlab down**. **netlab down --cleanup** removes the files it created. The process is not started when you use **netlab up --no-tools**.
* Each run executes all validation tests on the lab devices. Set the interval to match your devices; running the tests often can be slow and noisy on VM-based devices.
* The background process also stops when the lab snapshot disappears, after 12 hours, or after 20 failed **netlab validate** runs in a row.
* The plugin does nothing when you use **netlab up --dry-run** or **netlab down --dry-run**.

You can change the plugin behavior with these **tools.network_xray** parameters:

| Parameter | Meaning | Default |
|---|---|---|
| validate | Run the validation loop | False |
| validate_interval | Time (in seconds) between **netlab validate** runs | 30 |
| validate_max_hours | Stop the background process after this many hours | 12 |

Invalid **validate_interval** or **validate_max_hours** values (not a positive number) are replaced with the default values, and the plugin prints a warning.
