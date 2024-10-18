(netlab-config)=
# Deploying Custom Device Configurations

**netlab config** uses an internal Ansible playbook (`netsim/ansible/config.ansible`) to deploy custom device configurations generated from the supplied Jinja2 template(s) to lab devices. It takes lab parameters from the _netlab_ snapshot file and Ansible inventory created by the **[netlab create](netlab-create)** or **[netlab up](netlab-up)** command.

You have to use **netlab config** on a running lab. If you want to try out the configuration templates without starting the lab,  add the [**config** attribute](custom-config) to node data and run **netlab create** (to create the Ansible inventory) followed by **[netlab initial -c -o](netlab-initial)** to create the configuration files.

```

## Usage

```text
usage: netlab config [-h] [-r] [-v] [-q] template

Deploy custom configuration template

positional arguments:
  template       Configuration template or a directory with templates

options:
  -h, --help     show this help message and exit
  -r, --reload   Reload saved device configurations
  -v, --verbose  Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet    Report only major errors

All other arguments are passed directly to ansible-playbook
```

## Selecting Configuration Template

The configuration template specified in the **netlab config** command can be a Jinja2 template (**netlab config** automatically adds the `.j2` suffix) or a directory of configuration templates.

When you specify a directory name, the **netlab config** command tries to find the configuration template for individual lab devices using node name, `netlab_device_type`, and `ansible_network_os` Ansible variables, allowing you to create a set of templates to deploy the same functionality to lab devices running different network operating systems.

See [](custom-config), [](netlab-initial-custom) and [](dev-find-custom) for more details.

## Limiting the Scope of Configuration Deployments

All unrecognized parameters are passed to the internal `config.ansible` Ansible playbook. You can use **ansible-playbook** CLI parameters to modify the configuration deployment, for example:

* `-l` parameter to deploy device configurations on a subset of devices.
* `-C` parameter to run the Ansible playbook in dry-run mode.

## Restoring Saved Device Configurations

**netlab config --reload** implements the *reload saved device configurations* part of the **netlab initial -r** command. It waits for devices to become ready (because it's used immediately after a lab has been started) and starts the initial configuration process on devices that need more than a replay of saved configuration ([more details](netlab-up-reload)).

After that, it treats the saved device configurations as custom templates and uses the same process as the regular **netlab config** command.

## Debugging Device Configurations

To display device configurations within the Ansible playbook without deploying them, use `-v --tags test` parameters after the template name. 

The `-v` flag will trigger a debugging printout, and the bogus `test` flag will skip the actual configuration deployment.
