(extool-nuts)=
# Network Unit Testing System (NUTS)

[NUTS](https://github.com/network-unit-testing-system/nuts) is a Pytest plugin that enables automated network testing using simple YAML files. It’s ideal for validating your network configuration and state.

* Add the following lines to the lab topology file to use NUTS with _netlab_:

```
tools:
  nuts:
```

Then use one of the following commands to interact with the test container:

* `netlab connect nuts` — Runs pytest inside the NUTS Docker container.

* `netlab connect nuts bash` — Opens a shell in the NUTS Docker container for manual test execution and debugging.

All necessary files (including default test templates) are created in the `nuts/` directory and mounted automatically into the container.


**Test Drivers and Compatibility**

NUTS built-in Test Bundles rely on [NAPALM](https://github.com/napalm-automation/napalm) and [Netmiko](https://github.com/ktbyers/netmiko) drivers to interact with network devices. It is primarily tested with standard NAPALM drivers, ensuring wide compatibility across multiple platforms (e.g., Cisco IOS, Juniper JunOS, Arista EOS).

**Where to Find and Customize Tests**

When you generate a lab with NUTS enabled, the system creates default test cases in the `nuts/test/` directory. These are meant as starting templates, and you should customize them based on your specific testing requirements.

You can:

- Modify existing YAML test files.
- Add new YAML files with test parameters for different features.
- [Write your own NUTS test bundles.](https://nuts.readthedocs.io/en/latest/dev/writetests.html)
- If needed, you can also write custom Pytest tests in the `nuts/test/` directory.
