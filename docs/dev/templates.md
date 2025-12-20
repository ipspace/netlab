(dev-templates)=
# Jinja2 Extensions in netlab Configuration Templates

Starting with release 26.01, _netlab_ generates all configuration files internally using the standard Jinja2 Python library. This approach makes _netlab_ more stable and independent of Ansible whims (and associated headaches), but also makes most Ansible-specific Jinja2 filters unavailable in _netlab_ configuration templates.

## Additional Jinja2 Filters

However, to make it easier to write configuration templates for network devices, _netlab_ includes an independent implementation of these Ansible filters:

* **ipaddr**, **ipv4**, **ipv6**, and **hwaddr**, either as simple filter names or with **ansible.utils** or **ansible.netcommon** prefix
* **combine**, **difference**, **flatten**, **to_yaml**, and **to_nice_yaml**, either as simple filter names or with **ansible.builtin** prefix

```{note}
The **‌to_yaml** and **‌to_nice_yaml** filters return identical results -- nicely formatted YAML strings. The extra arguments used with these filters are ignored
```

Please open a [GitHub issue](https://github.com/ipspace/netlab/issues) if you use another Ansible-specific Jinja2 filter in your templates.

The **ipaddr**, **ipv4**, and **ipv6** filters recognize these arguments:

|argument | meaning |
|---|---|
| no argument | Select IP addresses from input string or list |
| integer or<br>number as string | Return N-th IP address in the input subnet as a CIDR prefix |
| **address** | Return the input value as an IP address (without the prefix)
| **host** | Generate an IP prefix from the input address or prefix |
| **prefix** | Return the prefix length of the input IP prefix |
| **subnet** | Return the input value as a CIDR prefix |
| other arguments | Return the corresponding `netaddr.IPNetwork` attribute |

```{warning}
The **‌ipaddr** filter does not accept **‌bool** input values. The input value must be a string or a list (if you use **‌ipaddr** with no extra arguments).

You don't have to check the validity of IP addresses for _netlab_ attributes; _netlab_ does that during the input data validation phase. To differentiate between unnumbered interfaces (where the **‌ipv4** or **‌ipv6** interface attribute is set to *‌True*) and numbered interfaces, use the `intf.ipv4 is string` test.
```

## Undefined Variables

_netlab_ emulates the Ansible implementation of undefined variables that allows you to test the presence of an element in a nested dictionary without checking the presence of the parent variable.

For example:

* You can test whether `loopback.ipv4 is defined` even on nodes that have no **loopback** interface. Standard Jinja2 would require you to use `loopback is defined and loopback.ipv4 is defined`.
* You can use the **default** filter on elements in nested dictionaries. For example, `loopback.ipv4|default('10.0.0.1')` will return `10.0.0.1` if the loopback interface has no IPv4 address, or if the device has no loopback interface.

```{warning}
Do not use undefined values with the **‌ipaddr** filter. If you think you have to check the input data against the **‌ipaddr** filter, use `some_input is defined and some_input|ipaddr`. Alternatively, use `some_input|default('')|ipaddr`
```

For consistency with built-in configuration templates, use `is defined` instead of `"key" in dictionary`. For example, use `loopback.ipv4 is defined` instead of `"ipv4" in loopback`. Unless you can safely assume that the **loopback** is a dictionary, a safer test using the "a in b" paradigm is `loopback is defined and "ipv4" in loopback`.
