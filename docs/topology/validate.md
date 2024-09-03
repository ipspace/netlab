(validate)=
# Lab Validation Tests

Lab topology can include a series of automated tests. Once the lab runs, you can execute those tests with the **[netlab validate](../netlab/validate.md)** command. The tests can be used in any automated validation process, from checking self-paced training solutions to integration tests and CI/CD pipelines.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(validate-tests)=
## Specifying Validation Tests

The **validate** topology element is a dictionary of tests. Those tests are executed in the order specified in the lab topology.

Each test has a name (dictionary key) and description (dictionary value) -- another dictionary with these attributes:

* **nodes** (list, mandatory) -- the lab nodes (hosts and network devices) on which the test will be executed.
* **devices** (list, optional) -- platforms (network operating systems) that can be used to execute the validation tests. The value of this parameter is set automatically in multi-platform tests; you have to supply it if you specified **show** and **exec** parameters as strings.
* **show** (string or dictionary) -- a device command executed with the `netlab connect --show` command. The result should be valid JSON.
* **exec** (string or dictionary) -- any other valid network device command. The command will be executed with the `netlab connect` command.
* **config** (string or dictionary) -- the configuration template that has to be deployed (using **[netlab config](netlab-config)**) on the specified nodes. Use this feature to trigger changes (for example, interface shutdown or BGP session shutdown) during the testing procedure.
* **suzieq** (string or dictionary) -- the SuzieQ command to execute and the optional validation parameters ([more details](validate-suzieq)).
* **valid** (string or dictionary, optional) -- Python code that will be executed once the **show** or **exec** command has completed. The test succeeds if the Python code returns any value that evaluates to `True` when converted to a boolean[^TEX]. The Python code can use the results of the **show** command as variables; the **exec** command printout is available in the `stdout` variable.
* **plugin** (valid Python function call as string, optional) -- a method of a custom [validation plugin](validate-plugin) that provides either a command to execute or validation results.
* **wait** (integer, optional) -- Time to wait (when specified as the only action in the test) or retry (when used together with other actions). The first wait/retry timeout is measured from when the lab was started; subsequent times are measured from the previous test containing the **wait** parameter.
* **wait_str** (string, optional) -- Message to print before starting the wait.
* **stop_on_error** (bool, optional) -- When set to `True`, the validation tests stop if the current test fails on at least one of the devices.
* **level** (string, optional) -- When set to `warning,` the test failure does not indicate that the whole testing sequence has failed but generates a warning message. 

[^TEX]: Objects, non-empty strings, lists, or dictionaries, integers not equal to zero or `True`. 

You can also set these test string attributes to prettify the test results:

* **description**: one-line description of the test
* **fail**: message to print when the test fails
* **pass**: message to print when the test succeeds

The **show**, **exec**, and **valid** parameters can be strings or dictionaries. If you're building a lab that will be used with a single platform, specify them as strings; if you want to execute tests on different platforms, specify a dictionary of commands and Python validation snippets. The values of these parameters can be Jinja2 expressions (see [](validate-multi-platform) for more details).

The **config** parameter can be a string (the template to deploy) or a dictionary with two parameters:

* **template**: the template to deploy
* **variable**: a dictionary of variable values that will be passed to the Ansible playbook as external variables. You can use these variables to influence the functionality of the configuration template ([example](validate-config))

**Notes:**

* Every test entry should have **show**, **exec**, **config**, **suzieq** or **wait** parameter.
* A test entry with just the **wait** parameter is valid and can be used to delay the test procedure.
* Test entries with **show** parameter must have **valid** expression.
* Test entries with **valid** expression must have **show**,  **exec**, or **suzieq** parameter.

```{tip}
A test entry with only **‌wait** and **‌stop_on_error** parameters is a *‌failure barrier*. It succeeds (without waiting) if all the prior test entries have passed and exits the validation process if at least one of the prior tests has failed.
```

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
  wait:
    description: Waiting for STP and OSPF to stabilize
    wait: 45

  ping:
    description: Ping-based reachability test
    nodes: [ h1,h2 ]
    devices: [ linux ]
    exec: ping -c 5 -W 1 -A h3
    valid: |
      "64 bytes" in stdout
```

(validate-retry)=
## Retry Validations Example

Instead of waiting a fixed amount of time, you can specify the **wait** parameter together with other test parameters. **netlab validate** will keep retrying the specified action(s) and validating their results until it gets a positive outcome or the wait time expires.

For example, the following validation test checks whether H1 and H2 can ping H3, retrying for at least 45 seconds.

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

```{tip}
When retrying the validation actions, **‌netlab validate** executes them only on the nodes that have not passed the validation test. The failure notice is printed only after the wait time expires, resulting in concise output containing a single PASS/FAIL line per node.
```

(validate-multi-platform)=
## Complex Multi-Platform Example

The following validation test is used on the ISP router in the [Configure a Single EBGP Session](https://bgplabs.net/basic/1-session/) lab to check whether the user configured an EBGP session with the ISP router.

```{tip}
The test will be used by students configuring BGP routers. The test includes the **description**, **pass**, and **fail** parameters to make the test results easier to understand.
```

```
session:
  description: Check the EBGP session on the ISP router
  fail: The EBGP session with your router is not established
  pass: The EBGP session is in the Established state
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

The test uses a **show** command that produces JSON printouts on Cumulus Linux, FRR, and Arista EOS. Cisco IOSv cannot generate JSON printouts; the command to execute on Cisco IOSv is therefore specified in the **exec** parameter.

The **valid** expressions for Cumulus Linux, FRR, and Arista EOS use JSON data structures generated by the **show** commands. These expressions could be simple code snippets like `ipv4Unicast.peers["10.1.0.1"].state == "Established"`, but using that approach risks breaking the tests if the device IP addresses change. The Jinja2 template:

* Iterates over the BGP neighbors of the ISP router.
* Selects the neighbor data belonging to the user router based on its name.
* Inserts the neighbor IP address of the user router in the Python code.

A similar approach cannot be used for Cisco IOSv. The only way to validate the correctness of a show printout is to use a convoluted regular expression.

```{tip}
* You can use the **‌netlab validate -vv** command to generate debugging printouts to help you determine why your tests don't work as expected.
* **‌netlab validate** command takes the tests from the `netlab.snapshot.yml` file created during the **‌netlab up** process. To recreate that file while the lab is running, use the hidden **‌netlab create --unlock** command.
* Use [validation plugins](validate-plugin) to create complex validation tests.
```

(validate-config)=
## Making Configuration Changes During the Validation Test

Imagine you want to test the OSPFv2 default route origination that depends on a BGP default route. You could use the following approach:

* Change the BGP configuration on a BGP neighbor to send the default route
* Verify that the external default route is present in the OSPF topology database
* Change the BGP configuration on a BGP neighbor to stop sending the default route
* Verify that the external default route is no longer present in the OSPF topology database.

You could use the following configuration template to advertise the BGP default route from Cisco IOS, FRRouting, or Arista EOS. Please note we're using the **df_state** variable to specify whether the default route should be advertised or not.

```
router bgp {{ bgp.as }}
!
{% for af in ['ipv4','ipv6'] %}
{%   for ngb in bgp.neighbors if af in ngb %}
{%     if loop.first %}
  address-family {{ af }}
{%     endif %}
    {% if df_state|default('') == 'off' %}no {% endif %}neighbor {{ ngb[af] }} default-originate
{%   endfor %}
{% endfor %}
```

Now that we have the Jinja2 template that changes the BGP default route origination, we could turn the above idea into a _netlab_ validation test using the FRR [validation plugins](validate-plugin)[^CVNN]

[^CVNN]: **xf** is the BGP neighbor of the device we're testing; **probe** is its OSPF neighbor

```yaml
bgp_dr:
    description: Enable BGP default route
    config: bgp_default
    pass: BGP default route is sent to BGP neighbors
    nodes: [ xf ]
  df_c:
    description: Check for the conditional default route
    wait_msg: Wait for SPF to complete
    wait: 10
    nodes: [ probe ]
    plugin: ospf_prefix('0.0.0.0/0')
  bgp_ndr:
    description: Disable BGP default route
    config:
      template: bgp_default
      variable.df_state: 'off'
    nodes: [ xf ]
    pass: BGP default route is no longer sent to BGP neighbors
  df_x:
    description: Check the OSPF default route is no longer advertised
    wait_msg: Wait for SPF to complete
    wait: 10
    nodes: [ probe ]
    plugin: ospf_prefix('0.0.0.0/0',state='missing')
```

(validate-plugin)=
## Validation Plugins

Simple validation tests are easy to write, particularly if you can hard-code node names or IP addresses in the **show**, **exec**, and **valid** parameters.

Jinja2 templates within the validation parameters can bring you further, but they tend to become complex and challenging to read or maintain. Even worse, you might have to copy-paste them around if you have a set of labs with similar validation requirements.

Validation plugins address those shortcomings and allow you to build a complex, flexible, and reusable validation infrastructure. They are loaded from the **validate** subdirectory of the lab topology directory or another set of locations specified in the **defaults.paths.validate** list.

The validation plugin directory must contain a Python file matching the device name for every _netlab_-supported platform you want to use in the validation tests. For example, the _netlab_ [OSPFv2 integration tests](https://github.com/ipspace/netlab/tree/dev/tests/integration/ospf/ospfv2) use FRR containers as external probes on which they run validation tests; the **validate** subdirectory thus contains a single file: `frr.py`.

Once you create the validation plugins, you can use their methods in the validation tests. For example, the OSPFv2 FRR validation plugin can check whether an FRR container has a specified OSFP neighbor:

```
validate:
  adj:
    description: Check for OSPF adjacencies
    nodes: [ x1, x2 ]
    plugin: ospf_neighbor(nodes.dut.ospf.router_id)
```

The validation process uses the **plugin** parameter to:

* Find whether it should execute a **show** command or another **exec** command on the device. Assuming a validation test **plugin** parameter uses function XXX, the validation code executes a **show** command if the device validation plugin has the **show_XXX** function and an **exec** command if the plugin has the **exec_XXX** function. 
* Get the string to execute on the device. The validation code calls the **show_XXX** or **exec_XXX** function with the parameters specified in the **plugin** parameter and executes the returned string on the lab device.
* Invoke the validation function. The validation code calls the **valid_XXX** function and uses its return value as the validation result.

For example, you can use `show ip ospf neighbor x.x.x.x json` on FRR containers to check for the presence of an OSPF neighbor. The **show_ospf_neighbor** function in the FRR validation plugin returns that string when given the neighbor router ID as an input parameter:

```
def show_ospf_neighbor(id: str) -> str:
  return f'ip ospf neighbor {id} json'
```

The validation function takes the results of the **show** command and checks whether they contain information about an OSPF neighbor with router ID given as the input parameter:

```
def valid_ospf_neighbor(id: str) -> bool:
  global _result
  if not id in _result.default:
    raise Exception(f'There is no OSPF neighbor {id}')
  
  n_state = _result.default[id]
  n_state = n_state[0]
  if n_state.converged != 'Full':
    raise Exception(f'Neighbor {id} is in state {n_state.nbrState}')

  return True
```

### Input Parameters

The function calls specified in the **plugin** validation test parameter can contain arguments that can be constants or local variables. The following local variables can be used:

* Any topology value. For example, you can use the `nodes` dictionary, the `links` list, or any expression that evaluates to a valid topology element, for example, `nodes.dut.ospf.router_id`.
* Current node parameters are available in the `node` variable. For example, use `node.name` to get the node name on which the test is executed or `node.ospf.router_id` to get the local OSPF router ID.
* The validation function can access the parsed results of the **show** or **exec** command as the global `_result` variable.

The same input parameters are passed to **show_XXX**, **exec_XXX**, and **valid_XXX** functions. If you want flexible validation functions, they might need many arguments that are irrelevant to the **show_XXX**/**exec_XXX** functions. In that case, use the `**kwargs` parameter to ignore the extra parameters, for example:

```
def show_bgp_neighbor(ngb: list, n_id: str, **kwargs: typing.Any) -> str:
  return 'bgp summary json'

def valid_bgp_neighbor(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',
      state: str = 'Established',
      intf: str = '') -> str:
...
```

### Return Values

* The **show_XXX** and **exec_XXX** functions should return the string to execute on the tested node.
* The **valid_XXX** function should return *False* if the validation failed, and *True* or a string value if the validation succeeded. The string value returned by the **valid_XXX** function is used as the *validation succeeded* message by the `netlab validate` command.

### Error Handling

The Python expression specified in the **plugin** argument might generate an execution error -- for example, the OSPF neighbor might not have the `ospf.router_id` parameter. Further errors might be generated or raised when a plugin function is executed.

Execution errors in **show_XXX** or **exec_XXX** functions result in standard _netlab_ error messages, while the execution errors in **valid_XXX** function indicate a failed validation test. The **valid_XXX** function can also raise exceptions to generate custom error messages.

For example, an FRR container might have an OSPF neighbor but could be stuck in the DBD exchange phase. The validation function thus has to check the state of the specified OSPF neighbor and raise an error with a custom error message if the adjacency is not fully converged:

```
  n_state = _result.default[id][0]
  if n_state.converged != 'Full':
    raise Exception(f'Neighbor {id} is in state {n_state.nbrState}')
```

(validate-suzieq)=
## Lab Validation with SuzieQ

You can [collect lab device information](extool-suzieq) with [SuzieQ](https://suzieq.readthedocs.io/en/latest/) observability tool and use SuzieQ commands in validation tests. 

The SuzieQ command to execute can be specified in the **suzieq** validation test parameter; **netlab validate** will assume you expect SuzieQ to return data and expect at least one of the returned records to be valid (if you use the **valid** function).

If you want to modify the test parameters, use the **suzieq** dictionary with the following keys:

* **show** -- the command to execute
* **expect** -- set to **empty** if you expect SuzieQ not to find any relevant data.
* **valid** -- set to **any** if you expect at least one returned record to pass further validation or to **all** if you expect all returned records to pass validation.

```{tip}
**netlab validate** always adds **format=json** and **hostname=_nodename_** to the command specified in the **‌suzieq** parameter
```

### Simple Examples

Let's assume we have a simple lab topology running BGP but not MLAG. The following test will execute SuzieQ command **bgp show hostname=r3 format=json** and succeed if SuzieQ returns at least one record (at least one BGP session is configured on the device):

```
validate:
  check_bgp:
    description: Is BGP active?
    suzieq: bgp show
    nodes: [ r3 ]
    pass: BGP is active
    fail: BGP is not active
```

To check for *lack of* MLAG, we have to tell **netlab validate** that we expect an empty list from SuzieQ with the **expect** keyword:

```
validate:
  check_mlag:
    description: Check for lack of MLAG
    suzieq:
      show: mlag show
      expect: empty
    nodes: [ r1 ]
    fail: MLAG is active on R1
```

### SuzieQ Result Validation

Finally, you can use a validation expression on every record returned by SuzieQ. The test will pass if _any_ (default) or _all_ (set with the **suzieq.valid** parameter) records pass the validation test.

For example, you could use the following test to check whether all BGP sessions on a node pass the SuzieQ BGP Assertion test. The test will execute `bgp assert hostname=r1 format=json` and `bgp assert hostname=r2 format=json` SuzieQ command.

```
  v4:
    suzieq:
      show: bgp assert
      valid: all
    nodes: [ r1, r2 ]
    valid: state == 'Established' and _assert == 'pass'
```

```{tip}
**‌assert** is a reserved word in Python. **‌netlab validate** converts the **‌assert** value in the returned record into **‌_assert** variable to allow you to check its value.
```
