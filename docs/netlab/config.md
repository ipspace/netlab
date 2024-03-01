# Deploying Custom Device Configurations

**netlab config** uses an internal Ansible playbook (`netsim/ansible/config.ansible`) to deploy custom device configurations generated from the supplied Jinja2 template(s) to lab devices.

```{tip}
**netlab config** command does not need a topology file (so you don't have to specify one even if you're using a non-default topology name). It's just a thin wrapper around an Ansible playbook that uses Ansible inventory created by the **netlab create** or **netlab up** command.
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

When the configuration template specified in the **netlab config** command is not a Jinja2 template, the command tries to find the configuration template for individual lab devices using node name, `netlab_device_type`, and `ansible_network_os` Ansible variables, allowing you to create a set of templates to deploy the same functionality to lab devices running different network operating systems.

See [](netlab-initial-custom) and [](dev-find-custom) for more details.

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
