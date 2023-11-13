# Version-Specific Lab Topology Files

_netlab_ offers two mechanisms you can use when working on projects that might be used in environments with unknown _netlab_ versions:

* Minimum *netlab* version required to run the lab topology.
* Version-specific topology files

## Minimum Netlab Version

You can specify minimum version required to run a lab topology in **version** attribute or in **defaults.version** attribute. The value of this attribute could be a simple version number (example: `1.6.4`) or a Python version specifier (example: `>= 1.6.3`).

For example, this is how you can ensure that _netlab_ generates a useful error message when a user tries to run a lab topology that uses **bgp.policy** plugin (introduced in release 1.6.4):

```
module: [ bgp ]
plugin: [ bgp.policy ]

version: 1.6.4
```

```{warning}
The **version** attribute was introduced in [_netlab_ release 1.6.3](release-1.6.3). Prior _netlab_ versions will report an invalid attribute.
```

## Version-Specific Topology Files

Starting with _netlab_ 1.6.4, _netlab_ tries to find a topology file that is a best match for the installed _netlab_ version.

When given a lab topology name (example: `topology.yml`), _netlab_ tries to find matching files that include a version number (example: `topology.*.*.yml`)[^2ED].

For example, when a directory contains `test.yml`, `test.1.5.yml`, `test.1.6.3.yml`, `test.1.6.yml`, and `test.1.8.yml`, _netlab_ uses the following topology when you execute `netlab up test.yml`

* `test.yml` for releases prior to 1.6.4 (the version-specific topologies were introduced in 1.6.4)
* `test.1.6.3.yml` in releases starting from 1.6.4 and up to 1.8
* `test.1.8.yml` in releases starting from 1.8.0.

```{tip}
It's highly recommended that you add **version** attribute to versioned topology files to ensure the user does not try to use a topology file not suitable for their _netlab_ version
```

Using version-specific topology files can be confusing. To reduce the confusion, _netlab_ prints a notice telling you which topology file it uses whenever it uses a version-specific topology file. You can also use the **netlab inspect input** command to display the topology file and all the default files _netlab_ used to start the lab, for example:

```
$ netlab inspect input
- /home/user/BGP/policy/6-med/topology.1.6.4.yml
- /home/user/BGP/defaults.yml
- /home/user/.netlab.yml
- package:topology-defaults.yml
```

[^2ED]: The version-specific topology name must include at least two extra dots to reduce the chance of a false positive.