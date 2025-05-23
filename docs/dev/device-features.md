# New Configuration Features for an Existing Device

If you want to fix a configuration template for an existing device supported by *netlab*, find the relevant configuration template ([initial configurations](devices.md#initial-device-configuration), [configuration modules](devices.md#configuration-modules)), fix it, test your changes, and [submit a PR](guidelines.md).

If you want to add support for a new configuration module (example: MPLS segment routing on Nexus OS):

* Read the [module documentation](../module-reference.md) to understand the configurable parameters;
* Using existing configuration templates as a rough guide create a new configuration template ([naming convention](devices.md#configuration-modules));
* Add new module under **features** parameter of device settings (see for example `netsim/devices/frr.yml`). If the device does not support any module-specific features (or if the module does not use features), set the value to **True**.
* Find relevant test topologies in `tests/topology/input` or `tests/integration` or create your own test topologies. The test topologies should (A) test all configurable parameters and (B) test devious parameter combinations.
* Create virtual labs using the selected test topologies and your device. The simplest way to achieve that is to set the device type with `-d` parameter of **netlab up** or **netlab create** command.
* If possible, create virtual labs with mixed device types to verify interoperability of your configuration settings (example: running OSPF on unnumbered interfaces requires an extra configuration command on Arista EOS).
* Update the [supported platforms](../platforms.md) documentation and add [caveats](../caveats.md) (if needed).
* [Submit a PR](guidelines.md).

You'll find more details in the [](dev-config-implementation).
