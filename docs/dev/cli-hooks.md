(dev-cli-hooks)=
# CLI Hooks

Several [**netlab** CLI commands](netlab-cli) can execute configurable commands during their operation. This functionality is configured in **netlab._command_** [topology defaults](topo-defaults) and is currently available in **[netlab up](netlab-up)** and **[netlab down](netlab-down)** commands.

Each CLI hook can specify a single CLI command (a string value). The commands executed as CLI hooks must be *executable* programs or scripts, not internal shell commands. For example, it's perfectly fine to use `touch some_file`, `bash some_script.sh`, or `python3 my_script.py`, but not `echo x`. Output redirection is not supported; if you need it, create a **bash** script to handle it.

You can use the error exit status of the external commands to stop **netlab** processing -- **netlab** will display a fatal error and stop its operation whenever an external command returns a non-zero exit status.

## Example

You could emulate the behavior of the `netlab.lock` locking file with these CLI hooks:

```
defaults.netlab:
  up.pre_start_lab: touch lab.lock
  down.post_stop_lab: rm lab.lock
```

The above defaults define commands that are executed [before the lab is started](dev-cli-hooks-up) and [after the lab is stopped](dev-cli-hooks-down).

After having the mechanism to create and delete the locking file, you could add **netlab.up.pre_probe** hook to check whether the locking file exists.

## Environment Variables Available to CLI Hooks

CLI parameters specified in the **netlab up** and **netlab down** commands are passed to the CLI hooks as environment variables starting with `NETLAB_ARGS_`. **netlab** also sets the `NETLAB_ARGS_TOPOLOGY` variable to the name of the lab topology specified in the command line or stored in the transformed lab topology snapshot file.

For example:

* When you execute `netlab down --cleanup`, the CLI hooks will have the `NETLAB_ARGS_CLEANUP` environment variable set to `True`. 
* When `netlab up` is started with `-vvv` parameter, the `NETLAB_ARGS_VERBOSITY` environment variable will be set to 3.

```{tip}
* You can debug this process with the verbosity set to `-vvv` or more.
* If you execute other **netlab** commands in the CLI hooks, those commands get the values of the `NETLAB_ARGS_` environment variables in the **defaults.args** dictionary.
```

(dev-cli-hooks-up)=
## netlab up Hooks

You can define external programs to be executed at these points in the *start the lab* process in the **defaults.netlab.up** dictionary:

* **pre_probe** -- executed before the "do we have a working environment" probe. Use this command to run additional checks on your environment (for example, whether [NETLAB_MULTILAB_ID](plugin-multilab) is set).
* **pre_start_lab** -- executed before any of the virtual machines or containers are started
* **post_start_lab** -- executed after the virtual machines and containers are running. You can use this command to add licenses to your virtual machines.

```{tip}
*‌containerlab* does not always check whether the containers are ready. If your script needs *‌operational* network devices, execute the `netlab initial --ready` command to ensure they are ready to be configured.
```

* **pre_initial_config** and **post_initial_config** are executed before and after the initial device configuration
* **pre_reload_config** and **post_reload_config** are executed before and after configuration reload. These commands are never executed in the same **netlab up** run as the initial device configuration hooks.
* **pre_tools_start** and **post_tools_start** are executed before and after the external tools are started.

**netlab up** can also call provider-specific hooks:

* **pre_start\__provider_** before a [virtualization provider](providers) is called to start the network devices
* **post_start\__provider_** after a [virtualization provider](providers) has started the network devices

For example, you could run `netlab initial --ready` after the containerlab has started the containers to ensure the network devices are ready (Vagrant waits for the device SSH server before declaring Mission Accomplished):

```
defaults.netlab.up.post_start_clab: netlab initial --ready
```

(dev-cli-hooks-down)=
## netlab down Hooks

You can define external programs to be executed at these points in the *stop the lab* process in the **defaults.netlab.down** dictionary:

* **pre_stop_lab** -- executed before the virtual machines and containers are stopped. You could use this script to deregister the licenses used by your network devices
* **post_stop_lab** -- executed after the virtual machines and containers have been stopped. You could use this command for further licensing processing that does not require access to network devices.

```{tip}
The **‌pre_stop_lab** hook will be executed every time the **‌netlab down** command is run. The **‌post_stop_lab** hook will be executed only when the lab is successfully stopped.
```

* **pre_cleanup** -- executed before **netlab down --cleanup** starts deleting the lab configuration files.
* **post_cleanup** -- executed after the cleanup process has been completed.

```{tip}
You can use any of the cleanup hooks to delete additional files that might have been created by your external commands.
```

**netlab down** can also call provider-specific hooks:

* **pre_stop\__provider_** before a [virtualization provider](providers) is called to stop the network devices
* **post_stop\__provider_** after a [virtualization provider](providers) has stopped the network devices
