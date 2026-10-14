(netlab-config)=
# Deploying Custom Device Configurations

**netlab config** is used to deploy custom device configuration templates to lab devices. It reads lab parameters from the _netlab_ snapshot file created by the **[netlab create](netlab-create)** or **[netlab up](netlab-up)** command, renders the supplied Jinja2 template ([limitations](dev-templates)), and uses the [device-specific configuration method](platform-config-mode) or the internal `config.ansible` Ansible playbook to deploy the rendered configuration snippets.

You have to use **netlab config** on a running lab. If you want to try out the configuration templates without starting the lab,  add the [**config** attribute](custom-config) to node data and run **netlab create** to create the configuration files.

## Usage

```text
usage: netlab config [-h] [-r] [-l LIMIT] [-e EXTRA_VARS [EXTRA_VARS ...]] [-v] [-q]
                     [-i INSTANCE]
                     template

Deploy custom configuration template

positional arguments:
  template              Configuration template or a directory with templates

options:
  -h, --help            show this help message and exit
  -r, --reload          Reload saved device configurations
  -l, --limit LIMIT     Limit the operation to a subset of nodes
  -e, --extra-vars EXTRA_VARS [EXTRA_VARS ...]
                        Specify extra variables for the configuration template
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  -i, --instance INSTANCE
                        Specify the lab instance to configure

All other arguments are passed directly to ansible-playbook
```

## Selecting Configuration Template

The configuration template specified in the **netlab config** command can be a Jinja2 template (**netlab config** automatically adds the `.j2` suffix) or a directory of configuration templates.

When you specify a directory name, the **netlab config** command tries to find the configuration template for individual lab devices using node name, `netlab_device_type`, and `ansible_network_os` Ansible variables, allowing you to create a set of templates to deploy the same functionality to lab devices running different network operating systems.

See [](custom-config), [](netlab-initial-custom) and [](dev-find-custom) for more details.

```{tip}
When executed with the `-i` option, **‌netlab config** expects the configuration template file or directory to be within the lab directory.
```

## Limiting the Scope of Configuration Deployments

* You can use the `-l` parameter to deploy device configurations on a subset of devices. The parameter value must be a valid _netlab_ node selection expression ([more details](netlab-inspect-node)).
* With the `--dry-run` parameter, you can display the commands that would be executed to configure the devices without executing them.
* Finally, the `--check` parameter uses Ansible's `--check` mode to display changes that would be made to the devices. This parameter uses Ansible for all device configurations (internal configuration methods cannot compare existing and target device configurations).

## Extra Variables

You can use the `-e` parameter to specify an extra variable value in the `name=value` format (the `-e` parameter can be used multiple times). _netlab_ recognizes only the `name=value` format, not the JSON or filename formats recognized by Ansible.

The extra variables are applied to all nodes and can be used in device configuration templates. For example, the following Jinja2 template uses the `df_state` variable to turn BGP default route advertisements on or off:

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

After saving the above template into `bgp_default.j2`, you can use `netlab config bgp_default --limit somenode` to enable BGP default route advertisement and `netlab config bgp_default --limit somenode -e df_state=off` to turn it off.

(netlab-config-reload)=
## Restoring Saved Device Configurations

**netlab config --reload** implements the *reload saved device configurations* part of the **netlab initial -r** command. It waits for devices to become ready (since it's used immediately after a lab has been started) and starts the initial configuration process on devices that need more than a replay of saved configuration ([more details](netlab-up-reload)).

After that, it treats the saved device configurations as custom templates (using the same process as the regular **netlab config** command), allowing you to use Jinja2 expressions in saved device configurations.

## Debugging Device Configurations

To create device configurations without deploying them, use the `--dry-run` parameter. **netlab config** command will create device configurations in the `node_files` directory tree, and then skip the configuration deployment.

The **netlab config** command also supports comprehensive debugging options. Use `--debug` to troubleshoot template search paths and template rendering.

For example:
- `netlab config my_template.j2 --debug template` - Debug Jinja2 template processing
- `netlab config my_template.j2 --debug all -vv` - Enable all debugging with verbose output

See [](dev-debug-flag) for complete documentation of all debugging options and which commands support them.

