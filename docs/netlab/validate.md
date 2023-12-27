# Validate Lab Network

**netlab validate** executes tests defined in the **validate** lab topology attribute on a running lab. You can use it in training labs to check whether the user has successfully completed the lab assignment.

## Usage

```text
$ netlab validate -h
usage: netlab inspect [-h] [-v] [--snapshot [SNAPSHOT]] [--list] [--node NODES] [tests ...]

Inspect data structures in transformed lab topology

positional arguments:
  tests                 Validation test(s) to execute (default: all)

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  --list                List validation tests
  --node NODES          Execute validation tests only on selected node(s)
  --skip-wait           Skip the waiting period
```

## Example

**netlab validate** command was executed on the [Advertise IPv4 Prefixes to BGP Neighbors](https://bgplabs.net/basic/3-originate/) lab before the user configured BGP prefix origination:

![netlab validate sample run](netlab-validate-example.png)
