(dev-debug)=
# Debugging netlab

This document describes the debugging flags, options, and techniques available in netlab for troubleshooting issues and understanding internal behavior.

## Command-Line Debugging Flags

(dev-debug-flag)=
### Primary Debug Flag (`--debug`)

The main debugging flag in netlab is `--debug [choices...]`. You can specify multiple choices separated by commas.

The following commands have built-in `--debug` support:

| Command | Description |
|---------|-------------|
| **[netlab create](netlab-create)** | Creates configuration files |
| **[netlab up](netlab-up)** | Start a lab |
| **[netlab initial](netlab-initial)** | Deploy initial device configurations |
| **[netlab config](netlab-config)** | Deploy custom configuration template to network devices |
| **[netlab validate](netlab-validate)** | Run validation tests specified in the lab topology |

You can specify these categories with the `--debug` flag (most categories are recognized by **netlab create** and **netlab up** commands, other commands implement a smaller subset of debugging options):

| Choice | Description |
|--------|-------------|
| `all` | Enable all debugging flags |
| `addr` | Debug addressing pools |
| `addressing` | Debug IPAM logic |
| `cli` | Debug CLI actions |
| `defaults` | Debug user/system defaults |
| `groups` | Debug netlab group processing |
| `links` | Debug the core link transformation code |
| `modules` | Debug generic configuration module routines |
| `plugin` | Debug plugin loading process and plugin calls |
| `template` | Debug common Jinja2 templating routines |
| `validate` | Debug the data validation logic |
| `vlan` | Debug VLAN module |
| `vrf` | Debug VRF module |
| `external` | Debug invocation of external programs |
| `libvirt` | Debug libvirt provider |
| `clab` | Debug containerlab provider |
| `status` | Debug the 'lab status' code |
| `quirks` | Debug device quirks code |
| `paths` | Debug search paths (helps troubleshoot custom templates) |
| `loadable` | Debug loadable modules |
| `lag` | Debug LAG (Link Aggregation) functionality |

**Usage Examples:**

```bash
# Enable all debugging
netlab create --debug all topology.yml

# Debug specific areas
netlab up --debug cli,links
netlab initial --debug template -vv

# Debug addressing issues
netlab create --debug addressing,vlan
```

### Verbose Flag (`-v`, `--verbose`)

The verbose flag is countable - you can use it multiple times for increased verbosity.

| Level | Usage | Description |
|-------|-------|-------------|
| Basic | `-v` or `-vv` | Basic verbose output |
| Extra | `-vvv` or higher | Extra verbose (prints command execution details) |

```bash
netlab up -v              # Basic verbose
netlab up -vv             # More verbose
netlab up -vvv            # Extra verbose (shows command execution)
```

### Other Useful Flags

| Flag | Description |
|------|-------------|
| `--log` | Enable basic logging |
| `-q`, `--quiet` | Report only major errors, suppress most output |
| `--dry-run` | Print commands that would be executed without running them |

```bash
# Dry run mode
netlab up --dry-run
netlab down --dry-run
netlab connect --dry-run host
```

## Environment Variables

### NETLAB_FAST_CONFIG
Enable fast configuration mode:
```bash
export NETLAB_FAST_CONFIG=1
```

### ANSIBLE_STDOUT_CALLBACK
Control Ansible output format:
```bash
export ANSIBLE_STDOUT_CALLBACK=selective  # Used for quiet mode
export ANSIBLE_STDOUT_CALLBACK=dense      # Used for collect/tarball commands
```

## Device-Specific Debugging

### Cisco IOS/IOS XE
Add debug commands to execute during initial configuration:
```yaml
nodes:
  router1:
    device: ios
    ios.debug:
      - ip routing
      - bgp ipv4 unicast updates
```

### FRRouting
Enable debug conditions:
```yaml
nodes:
  router1:
    device: frr
    frr.debug:
      - bgp ipv4 unicast updates
```

## Special Debugging Commands

### Debug Command
Load and execute a command module without exception handling (useful for debugging module import errors):
```bash
netlab debug <command> <parameters>
```

### Status Debugging
Show detailed lab status information, including logs:
```bash
netlab status --log
```

### Validation Debugging
Generate debugging printouts for validation tests:
```bash
netlab validate -vv
```

## Internal Debugging Flags

These flags are primarily used for internal testing and CI:

| Flag | Purpose |
|------|---------|
| `--test errors` | Disable error header printing (internal testing) |
| `--warning` | Raise warnings instead of printing them (CI flag) |
| `--raise_on_error` | Raise exceptions instead of aborting (CI flag) |

## Logging Configuration

netlab uses several logging levels and flags:

- **VERBOSE**: Integer level (0-3+), controls verbosity of output
- **LOGGING**: Boolean, enables basic logging
- **DEBUG**: List of active debug flags
- **QUIET**: Boolean, suppresses most output

You can programmatically check the above flags in your plugins as **netsim.utils.log._flag_**. You can also check if a debug flag is active using:

```python
from netsim.utils import log

if log.debug_active('cli'):
    print("CLI debugging is active")
```

## Getting Help

If you encounter issues that the above debugging tips can't help you resolve:

1. Check the [GitHub Issues](https://github.com/ipspace/netlab/issues) and [Discussions](https://github.com/ipspace/netlab/discussions) for similar problems
2. [Create a new issue](https://github.com/ipspace/netlab/issues/new/choose) and follow the instructions in the issue template.