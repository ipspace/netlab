# Deploying Custom Device Configurations

**netlab config** uses an internal Ansible playbook (`netsim/ansible/config.ansible`) to deploy custom device configurations generated from the supplied Jinja2 template(s) to lab devices.

## Usage

```text
usage: netlab config [-h] [-v] template

Deploy custom configuration template

positional arguments:
  template       Configuration template (or a family of templates)

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Verbose logging

All other arguments are passed directly to ansible-playbook
```

## Selecting Configuration Template

**netlab config** uses these steps trying to find the configuration template for individual lab devices:

* Combine template name with `ansible_network_os` and `.j2` suffix
* Use template name as specified
* Add `.j2` suffix to the template name.

The first step allows you to create a set of templates to deploy the same functionality to lab devices running different network operating systems. The last step allows you to specify just the template name without the `.j2` suffix.

## Limiting the Scope of Configuration Deployments

All unrecognized parameters are passed to internal `config.ansible` Ansible playbook. You can use **ansible-playbook** CLI parameters to modify the configuration deployment, for example:

* `-l` parameter to deploy device configurations on a subset of devices.
* `-C` parameter to run the Ansible playbook in dry-run mode.

## Debugging Device Configurations

To display device configurations from within the Ansible playbook without deploying them, use `-v --tags test` parameters after the template name. 

The `-v` flag will trigger debugging printout, and the bogus `test` flag will skip the actual configuration deployment.
