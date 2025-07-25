(node-debug)=
# Debugging Network Devices

It's usually trivial to enable debugging on devices running in a virtual lab:

1. Log in to the affected devices
2. Enable debugging
3. Monitor debugging outputs in log files or an SSH session

However, you might want to enable specific debugging printouts every time you start a lab topology. That's pretty easy to do on most devices that allow you to execute regular commands (for example, the **debug** command) within the configuration mode:

1. Create a [custom configuration template](custom-config) that enables debugging, for example:

   ```
   do debug ipv6 routing
   do debug bgp ipv6 unicast import events
   do debug bgp ipv6 unicast import updates
   do debug bgp ipv6 unicast updates out
   ```

2. Add the name of the custom configuration template to a node **config** list.

```{tip}
This approach allows you to automate debugging in a [multi-vendor environment](custom-config-multivendor)
```

Unfortunately (for debugging purposes), _netlab_ executes the custom configuration templates after configuring the network devices, which means you might lose the interesting part of the debugging information: what happens when the control-plane protocols start.

You can enable debugging *before* configuring network devices with this simple trick:

1. Execute **netlab up --no-config**
2. If needed, execute **netlab initial --ready** to ensure the network devices are fully operational
3. Log into the network devices and enable debugging, or use a custom configuration template and execute it with **netlab config _debugging_template_** (this approach yet again gives you multi-vendor capabilities).
4. Start device configuration with **netlab initial**

```{warning}
Some devices (for example, Arista EOS) accept debugging commands only after the corresponding control-plane protocol has been configured, making the above approach a non-starter.
```
