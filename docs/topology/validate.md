# Lab Validation Tests

Lab topology can include a series of automated tests. Once the lab runs, you can execute those tests with the **[netlab validate](../netlab/validate.md)** command. The tests can be used in any automated validation process, from checking self-paced training solutions to integration tests and CI/CD pipelines.

The **validate** topology element is a dictionary of tests that are executed in the order in which they're specified in the lab topology.

Each test has a name (dictionary key) and description (dictionary value) -- another dictionary with these attributes:

* **nodes** (list, mandatory) -- the lab nodes (hosts and network devices) on which the test will be executed.
* **devices** (list, optional) -- platforms (network operating systems) that can be used to execute the validation tests. The value of this parameter is set automatically in multi-platform tests; you have to supply it if you specified **show** and **exec** parameters as strings.
* **show** (string or dictionary) -- a device command executed with the `netlab connect --show` command. The result should be valid JSON.
* **exec** (string or dictionary) -- any other valid network device command. The command will be executed with the `netlab connect` command.
* **valid** (string or dictionary, optional) -- Python code that will be executed once the **show** or **exec** command has completed. The test succeeds if the Python code returns any value that evaluates to `True` when converted to a boolean[^TEX]. The Python code can use the results of the **show** command as variables; the **exec** command printout is available in the `stdout` variable.
* **wait** (integer, optional) -- Time to wait before starting the test. The first wait time is measured from when the lab was started; subsequent times are measured from the previous test containing the **wait** parameter.
* **wait_str** (string, optional) -- Message to print before starting the wait.
* **stop_on_error** (bool, optional) -- When set to `True`, the validation tests stop if the current test fails on at least one of the devices.

[^TEX]: Objects, non-empty strings, lists, or dictionaries, integers not equal to zero or `True`. 

You can also set these test string attributes to prettify the test results:

* **description**: one-line description of the test
* **fail**: message to print when the test fails
* **pass**: message to print when the test succeeds

The **show**, **exec**, and **valid** parameters can be strings or dictionaries. If you're building a lab that will be used with a single platform, specify them as strings; if you want to be able to execute tests on different platforms, specify a dictionary of commands and Python validation snippets. The values of these parameters can be Jinja2 expressions (see [](validate-multi-platform) for more details).

**Notes:**

* Every test entry should have **show**, **exec** or **wait** parameter.
* A test entry with just the **wait** parameter is valid and can be used to delay the test procedure.
* Test entries with **show** parameter must have **valid** expression.
* Test entries with **valid** expression must have either **show** or **exec** parameter.

(validate-simple)=
## Simple Example

The following validation test is used in a simple VLAN integration test that connects two hosts to the same access VLAN.

```
validate:
  ping:
    description: Pinging H2 from H1
    nodes: [ h1 ]
    devices: [ linux ]
    exec: ping -c 10 h2 -A
    valid: |
      "64 bytes" in stdout
```

The validation runs on Linux hosts, so there's no need for a multi-platform approach. The validation test executes a simple **ping** command on a host and checks whether at least one ping returned the expected amount of data (64 bytes).

(validate-wait)=
## Wait-before-Test Example

Control-plane protocols might need tens of seconds to establish adjacencies and reach a steady state. The following validation test waits for OSPF initialization (~40 seconds to elect a designated router on a LAN segment) before starting end-to-end connectivity tests:

```
validate:
  ping:
    description: Ping-based reachability test
    wait_msg: Waiting for STP and OSPF to stabilize
    wait: 45
    nodes: [ h1,h2 ]
    devices: [ linux ]
    exec: ping -c 5 -W 1 -A h3
    valid: |
      "64 bytes" in stdout
```

(validate-multi-platform)=
## Complex Multi-Platform Example

The following validation test is used on the ISP router in the [Configure a Single EBGP Session](https://bgplabs.net/basic/1-session/) lab to check whether the user configured an EBGP session with the ISP router:

```
session:
  description: Check EBGP session on ISP router
  fail: The EBGP session with your router is not established
  pass: The EBGP session is in Established state
  nodes: [ x1 ]
  show:
    cumulus: bgp summary json
    frr: bgp summary json
    eos: "ip bgp summary | json"
  exec:
    iosv: >
      show ip bgp summary

  valid:
    cumulus: >
      {% for n in bgp.neighbors if n.name == 'rtr' %}
      ipv4Unicast.peers["{{ n.ipv4 }}"].state == "Established"
      {% endfor %}
    frr: >
      {% for n in bgp.neighbors if n.name == 'rtr' %}
      ipv4Unicast.peers["{{ n.ipv4 }}"].state == "Established"
      {% endfor %}
    eos: >
      {% for n in bgp.neighbors if n.name == 'rtr' %}
      vrfs.default.peers["{{ n.ipv4 }}"].peerState == "Established"
      {% endfor %}
    iosv: >
      {% for n in bgp.neighbors if n.name == 'rtr' %}
      re.search('(?m)^{{ n.ipv4|replace('.','\.') }}.*?[0-9]$',stdout)
      {% endfor %}
```

The test will be used by students configuring BGP routers; it includes the **description**, **pass**, and **fail** parameters to make the test results easier to understand.

The test uses a **show** command that produces JSON printouts on Cumulus Linux, FRR, and Arista EOS. Cisco IOSv cannot generate JSON printouts; the command to execute on Cisco IOSv is therefore specified in the **exec** parameter.

The **valid** expressions for Cumulus Linux, FRR, and Arista EOS use JSON data structures generated by the **show** commands. These expressions could be simple code snippets like `ipv4Unicast.peers["10.1.0.1"].state == "Established"`, but using that approach risks breaking the tests if the device IP addresses change. The Jinja2 template:

* Iterates over the BGP neighbors of the ISP router.
* Selects the neighbor data belonging to the user router based on its name.
* Inserts the neighbor IP address of the user router in the Python code.

A similar approach cannot be used for Cisco IOSv. The only way to validate the correctness of a show printout is to use a convoluted regular expression.

```{tip}
* You can use the **‌netlab validate -vv** command to generate debugging printouts to help you determine why your tests don't work as expected.
* **‌netlab validate** command takes the tests from the `netlab.snapshot.yml` file created during the **‌netlab up** process. To recreate that file while the lab is running, use the hidden **‌netlab create --unlock** command.
```
