# Deploying Junos Configurations with NETCONF without Ansible

_netlab_ already uses NETCONF to configure Junos devices, but it does that through Ansible:

* The **junos** device (the parent of **crpd**, **vjunos-router**, **vjunos-switch**, **vmx**, **vptx**, and **vsrx**) sets **ansible_connection** to `netconf`.
* The `deploy-config/junos.yml` task list calls the **junos_config** module with the rendered configuration snippet as its **src** parameter. Because the snippet uses curly braces, the module sends it in a `<load-configuration action="merge" format="text">` RPC and then sends a `<commit>` RPC.
* `fetch-config/junos.yml` (**netlab collect**) uses **junos_facts**. `readiness-check/junos.yml` uses **junos_command**. Both go over the same NETCONF connection.

This document proposes an internal (Python) NETCONF configuration method that works the same way as the [*netmiko* configuration method](dev-config-netmiko). It would let you configure Junos devices without starting **ansible-playbook**.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Why Bother?

* **Speed.** The Ansible playbook starts a separate Ansible worker for each node, opens a persistent NETCONF connection, and commits each configuration snippet separately (initial, each module, each custom template). Junos commits are slow, often taking several seconds on vMX or vPTX. An internal method can load all the snippets into the candidate configuration and commit once.
* **Fewer dependencies.** A user running Junos-only labs would need *ncclient*, but not Ansible or the **junipernetworks.junos** collection.
* **Better error reporting.** A NETCONF `<rpc-error>` includes the error severity, message, and often the configuration path. _netlab_ can report those directly instead of filtering them out of an Ansible traceback.
* **Real configuration replace.** **netlab config --reload** could use `load override` (`action="override"`) instead of merging the saved configuration into the normalized device configuration.

### Why NETCONF and Not *netmiko*?

*netmiko* has a `juniper_junos` driver, but its **send_config_from_file** function sends configuration lines one at a time in configuration mode. That works with `set` commands, but not with curly-brace configurations. We would need `load merge terminal` followed by Ctrl-D, plus screen-scraping to detect errors. NETCONF accepts the template output without changes and returns structured errors. The Junos boxes _netlab_ builds already turn on NETCONF over SSH (see `netsim/install/libvirt/vsrx/juniper.conf`). The Ansible-based deployment proves the same is true for the other Junos images.

## Proposed Implementation

The proposal adds a new configuration method (`netconf`) next to `netmiko`. It reuses the existing plumbing for internal configuration deployment:

* The `_node_config` mapping set by **add_default_config_mode** (`netsim/providers/__init__.py`)
* The `netlab_ansible_skip_module` list
* The **INTERNAL_CONFIG_MECHANISMS** dictionary (`netsim/cli/initial/deploy.py`)
* The `_deploy` results that **print_internal_stats** displays

### Device Settings

The new device features go in the **features.netconf** dictionary. They mirror **features.netmiko**:

```
features:
  initial:
    config_mode: [ netconf ]
  netconf:
    device_params: { name: junos }  # ncclient device handler
    format: text                    # load-configuration format: text, set, or xml
    commit: once                    # 'once' (after the last snippet) or 'snippet'
    timeout: 300                    # RPC timeout (replaces ansible_command_timeout)
    collect: True                   # Use get-configuration in 'netlab collect'
    reload: override                # load-configuration action used by 'netlab config --reload'
```

To make NETCONF the default configuration method, set **group_vars.netlab_config_mode** to `netconf` in `junos.yml`. Until it's been tested on all Junos platforms, users can opt in with the **netlab_config_mode** node parameter or the **defaults.devices.junos.group_vars.netlab_config_mode** default.

The *libvirt* provider allows only the configuration modes listed in **defaults.providers.libvirt.config_mode** (`netsim/providers/libvirt.yml`), so `netconf` has to be added to that list.

### Connection Utilities (`netsim/utils/netconf.py`)

This module would be a near-copy of `netsim/utils/netmiko.py`:

* Import *ncclient* in a `try` block and set the **NCCLIENT_IS_MISSING** and **NCCLIENT_LOAD_ERROR** flags. **check_ncclient** reports the error the first time it's needed.
* **prepare_params** builds the `manager.connect` parameters:
  * **host**: **mgmt.ipv4**, or **mgmt.ipv6** when there's no IPv4 address
  * **port**: the **netlab_netconf_port** group variable, defaulting to 830
  * **username** and **password**: **ansible_user** and **ansible_ssh_pass**, using the same group variable translation as *netmiko*
  * **device_params** and **timeout**: from the device features
  * **hostkey_verify**: `False`, plus `look_for_keys=False` and `allow_agent=False`
* **connect** opens the session and sets `raise_mode` to `RaiseMode.ERRORS`. Junos returns warnings (for example, deleting a configuration element that doesn't exist) that must not abort the deployment.
* Session logging: point the `ncclient.transport.session` and `ncclient.operations.rpc` loggers at `node_files/<node>/netconf.log`, the way *netmiko* writes `netmiko.log`.

### Configuration Deployment (`netsim/cli/initial/netconf.py`)

This module works like `netsim/cli/initial/netmiko.py`, but uses the candidate datastore:

```python
def deploy(n_data: Box, topology: Box, n_deploy: list) -> None:
  ...
  with conn, conn.locked('candidate'):
    loaded = []
    for cfg_item in n_deploy:
      if node_config.get(cfg_item.replace('.','@'),None) != ':netconf':
        continue
      cfg_text = Path(f'node_files/{n_data.name}/{cfg_item}').read_text()
      try:
        conn.load_configuration(action='merge',format=nc_format,config=cfg_text)
        loaded.append(cfg_item)
        if commit_mode == 'snippet':
          conn.commit()
      except RPCError as ex:
        conn.discard_changes()
        append_to_list(n_data._deploy,'failed',cfg_item)
        log.error(f'{cfg_item} configuration failed on {n_data.name}',more_data=format_rpc_error(ex),...)
        return

    if commit_mode == 'once' and loaded:
      conn.commit()                       # Commit errors are attributed to all loaded snippets
    n_data._deploy.success = loaded
    n_data._deploy.method = 'NETCONF'
```

Things to watch:

* A `load-configuration` error can be traced to a specific snippet. A commit-time error (for example, a reference to an undefined policy) can't, because the commit validates the whole candidate configuration. When debugging is enabled (or after a failed single commit), the `snippet` commit mode makes it obvious which snippet broke the commit.
* `conn.locked('candidate')` fails if someone else is editing the configuration. An alternative is `<open-configuration><private/></open-configuration>`, which is more forgiving but slightly harder to use with *ncclient*.
* After a failure, **discard_changes** prevents a half-loaded candidate configuration from being committed later by someone else.
* **netlab config** (custom templates) already goes through **deploy_internal_config**, so it would get NETCONF support for free.

### Missing *ncclient* Library

**check_netmiko_config_mode** and **netmiko_fallback_config_mode** (`netsim/augment/nodes.py`) hardcode the `netmiko` method. They should become table-driven: map each configuration method to the Python module it needs (`netmiko` → *netmiko*, `netconf` → *ncclient*), and fall back to Ansible with a warning when that module can't be found. The **defaults.netmiko.installed** override needs a **defaults.netconf.installed** counterpart so the transformation tests stay independent of the installed packages.

The installation side:

* *ncclient* is already installed by `netlab install ansible`.
* Add it either to `netsim/install/netmiko.sh` (renamed to something like "Python device libraries") or to a new `netlab install netconf` script.
* *ncclient* depends on *paramiko* (already needed by *netmiko*) and *lxml* (binary wheels exist for all supported platforms).

### Readiness Checks

Junos devices use **netlab_ready: [ ansible ]**, with **features.command.ready** already defined (`show interfaces terse` must include the first physical interface). To drop Ansible completely:

* Add a `netconf` step to **READY_ACTIONS** (`netsim/cli/initial/ready/__init__.py`) that retries **manager.connect** until it works. NETCONF can lag behind the SSH server while the management daemon starts.
* Follow it with the existing **command** step, or run `<get-interface-information><terse/></get-interface-information>` over the same session.
* Set **netlab_ready** to `[ netconf, command ]` when the configuration method is `netconf`.

### Configuration Collection and Reload

* **netlab collect**: add `'netconf': netconf.collect` to the internal collection dictionary in `netsim/cli/collect/__init__.py`. The collector calls `get_configuration(format='text')` and saves the `<configuration-text>` contents. The output is the same curly-brace format that **junos_facts** produces today, so existing saved configurations stay compatible.
* **netlab config --reload**: add a NETCONF path next to **reload_with_netmiko** (`netsim/cli/config/reload.py`). It loads the saved configuration with `action="override"` and commits. There's no SCP step or device file system to worry about, and the result is a real configuration replace. The saved configuration must contain the management and login settings. Configurations collected with **netlab collect** do.

### Debugging

* Add `netconf` to the `--debug` choices of **netlab initial** (`netsim/cli/initial/utils.py`). When it's active, print the connection parameters (minus the password) and the RPC replies.
* Add a hint to every error message pointing to `node_files/<node>/netconf.log`.

## Open Issues

* **vMX license.** `tasks/vmx/initial.yml` copies and loads the evaluation license with `scp` and `ssh` before the initial configuration. We could either keep using Ansible for vMX nodes that set **netlab_license_url** or **netlab_license_file**, or send the license text with the `<request-license-add>` RPC. That RPC needs testing to see whether it accepts inline key data.
* **cRPD.** cRPD uses `ssh` readiness and a NETCONF Ansible connection. We need to check that its NETCONF subsystem is reachable on port 830 with the default containerlab configuration.
* **Single commit vs. per-snippet commits.** A single commit is the main speed gain. But it changes behavior when a template only validates on top of a previously committed snippet (it shouldn't, as they all merge into the same candidate configuration). Integration tests on every Junos platform will tell.
* **Other NETCONF devices.** The utilities aren't Junos-specific. Devices whose templates already produce something **load-configuration** or **edit-config** accepts could use them, and the **netconf.format** feature leaves room for that. SR OS would need its gNMI path/value template output converted to XML first, which is a separate project.

## Implementation Steps and Effort

1. `netsim/utils/netconf.py` (about 100 lines, mostly a *netmiko* utility clone)
2. `netsim/cli/initial/netconf.py` plus the **INTERNAL_CONFIG_MECHANISMS** registration (about 80 lines)
3. Table-driven fallback for missing libraries in `netsim/augment/nodes.py`, the **defaults.netconf.installed** override, and adding `netconf` to the *libvirt* configuration modes
4. Junos device features (**initial.config_mode**, **netconf.\***), initially opt-in
5. Collection and reload support (about 60 lines each)
6. A `netconf` readiness step
7. Documentation: `docs/dev/config/netconf.md` (with a `{features}` table like the *netmiko* one), plus updates to `docs/netlab/initial.md`, `docs/caveats.md`, and the release notes
8. Run the integration tests (`tests/integration`) on vjunos-router, vjunos-switch, vSRX, vPTX, vMX, and cRPD, first with `netlab_config_mode: netconf` and then as the default

Steps 1–4 deliver a usable opt-in configuration method; the rest can follow incrementally. Not counting the integration test runs (which are the slow part with Junos VMs), the coding effort is in the range of a few days.
