(integration-testing)=
# Integration Tests

*netlab* includes [over 200 integration tests](https://github.com/ipspace/netlab/tree/dev/tests/integration) and we use them to test correctness of device configuration templates and multi-vendor interoperability.

The tests are not yet run as part of a CI/CD pipeline (that would require significant investment in test infrastructure); you can run them manually or run a series of tests for a single platform. Automation scripts in the `integration_tests` branch are used for large-scale test runs. The tests run from the `integration_tests` branch also collect results that are then published either as [interim test results](https://tests.netlab.tools/) or [release documentation](https://release.netlab.tools/).

Most tests use FRR or EOS containers or virtual machines as probes (devices that can be used to check the correct operation of the tested device) and include validation procedures to check the correctness of the device configuration templates.

(integration-test-single)=
## Running a Single Integration Test

If you want to test your changes to a device configuration template:

* Select the relevant test from the `tests/integration` directory.
* Execute **netlab up -d _your_device_ _path_to_test_ \-\-validate** in an empty directory
* Check the validation results ;)

```{tip}
The `X` directory anywhere within the Git repository is untracked, making it an ideal place to run integration tests. You might want to use the `tests/X` directory to minimize the length of the relative paths, or use symbolic links. For example, you could execute `ln -s ../tests/integration/evpn .` to access EVPN integration tests as `evpn/*`.
```

(integration-test-suite)=
## Running an Integration Test Suite

Use the `device-module-test` script in the `tests/integration` directory to execute a series of related tests for a single device:

* Set the NETLAB_DEVICE environment variable to the device you want to test (for example, `export NETLAB_DEVICE=frr`)
* Set the NETLAB_PROVIDER environment variable to the provider you want to test (for example, `export NETLAB_PROVIDER=clab`)
* Within the `tests/integration` directory, execute the `device-module-test` Python script, specifying one or more test directories as its arguments.

For example, to run test **gateway** and **isis** integration tests, execute

```
./device-module-test gateway isis
```

**Notes:** 

* The tests are executed in the `/tmp/netlab_wk` directory. Change that directory with the `--workdir` parameter.
* The test results are collected in the `/tmp/netlab_log` directory. Change that directory with the `--logdir` parameter.
* The `device-module-test` script uses tests `[0-9]*yml` in the specified directory. Change that pattern with the `--limit` parameter.

For each test, the `device-module-test` executes:

* **netlab create** to create the configuration files. The "device does not support this feature" errors are caught in this phase.
* **netlab up --no-config** to start the lab. This phase should not produce any errors.
* **netlab initial** to configure the lab devices. This phase will expose any configuration template errors, either Jinja2 errors or configuration commands not recognized by the target device.
* **netlab validate** to run a series of checks validating the proper operation of the tested device. The validation errors are reported to the user; to store them in a file, use the `--batch` argument.

The results of individual **netlab** commands are stored in the logging directory. For example, the `gateway/01-anycast.yml` test produces these files in the `/tmp/netlab_log` directory:

```
$ ls -1 /tmp/netlab_log/01-anycast*
/tmp/netlab_log/01-anycast.yml-create.log
/tmp/netlab_log/01-anycast.yml-initial.log
/tmp/netlab_log/01-anycast.yml-up.log
```

A summary of the test results is also stored in the `results.yaml` file in the logging directory.

## Creating New Integration Tests

Add a new test into the `tests/integration` directory whenever you implement significant new functionality that needs to be tested across all netlab-supported platforms.

While writing the test, please follow these guidelines:

* Running a single integration test across all supported devices takes over 30 minutes (thank you, bloatware vendors). Add an integration test only when absolutely necessary.
* Integration tests are used to validate the correctness of device configuration templates, not to showcase your brilliance.
* An integration test should focus on a single feature or a small set of related features that are always available together.
* Use as little extra functionality as possible. For example, using VLANs or VRFs in OSPF integration tests makes no sense unless you're explicitly testing VLAN- or VRF-related functionality (for example, VLAN interface MTU).
* Use as few of the tested devices as feasible. Some devices are resource hogs; tests that pair a tested device with low-footprint probes execute faster.
* Use Linux or FRR for endpoints (hosts) and FRR or Arista EOS for probes.
* Unless necessary, use containers for hosts and probes. Notable exceptions include STP tests (we don't want to rely on Linux bridges working correctly) or LACP tests (Linux bridges drop LACP).
* Sometimes, you want to check whether devices support non-crucial functionality (for example, an IPv6 anycast gateway). Use **level: warning** in validation tests to generate a warning instead of a hard failure.

Sometimes it's easier to modify an existing validation test as long as:

* The new features you're adding work on all devices that already passed the integration test (it makes no sense to start failing an integration test just because you didn't feel like completing your job).
* It's still easy for a developer to figure out what's causing the integration test failure.
