(netlab-initial)=
# Deploying Initial Device Configurations

**netlab initial** command uses expanded Ansible inventory data created by the **[netlab up](up.md)** command, device-specific Jinja2 templates, and an internal Ansible playbook to deploy initial device configurations.

**netlab initial** skips devices with [**unmanaged** attribute](node-attributes) (those devices are not part of Ansible inventory) and [devices in the **unprovisioned** group](group-special-names).

After successful completion of the Ansible playbook, **netlab initial** displays the [help **message** defined in the lab topology](topology-reference-top-elements).

![netlab initial functional diagram](initial.png)

The Ansible playbook invoked by the **netlab initial** command deploys device configurations in four steps:

* Wait for devices to become ready[^rtag]
* Initial device configurations[^itag]
* Module-specific device configurations[^mtag]
* Custom configuration templates[^ctag]

[^rtag]: Use the `--ready` flag to execute just this step
[^itag]: Controlled by `-i` flag or **initial** Ansible tag
[^mtag]: Controlled by `-m` flag or **module** Ansible tag
[^ctag]: Controlled by `-c` flag or **custom** Ansible tag

Jinja2 templates are used together with **_device_\_config** Ansible modules to configure most devices. Sometimes, the configuration task list includes additional tasks[^init]. Some devices (for example, Fortinet firewall) are configured through calls to device-specific Ansible modules. See _[](../caveats.md)_ for more details.

[^init]: For example, Juniper vMX requires an evaluation license to be applied after the device boots.

```{tip}
* The **netlab initial** command reads the transformed lab data from the `netlab.snapshot.yml` file created by the **netlab up** command.
* When run with the **-v** parameter, the command displays device configurations before deploying them.
```

## Usage

```text
usage: netlab initial [--log] [-q] [-v] [-i] [-m [MODULE]] [-c]  [--ready] [--fast] [-o [OUTPUT]]

Initial device configurations

optional arguments:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -q, --quiet           Report only major errors
  -v, --verbose         Verbose logging
  -i, --initial         Deploy just the initial configuration
  -m [MODULE], --module [MODULE]
                        Deploy module-specific configuration (optionally including a 
                        list of modules separated by commas)
  -c, --custom          Deploy custom configuration templates (specified in "config" 
                        group or node attribute)
  --ready               Wait for devices to become ready
  --fast                Use "free" strategy in Ansible playbook for faster
                        configuration deployment
  -o [OUTPUT], --output [OUTPUT]
                        Create a directory with initial configurations instead of
                        deploying them

All other arguments are passed directly to ansible-playbook
```

## Wait for Devices to Become Ready

Some devices are not ready immediately after they complete the boot process. For example, Cisco Nexus OS or Juniper vPTX need another minute to realize they have data-plane interfaces.

Likewise, the virtualization provider might prematurely report that the devices are ready. For example, *containerlab*  does not wait for VMs running in containers to complete their boot process (see [](clab-vrnetlab) for more details).[^vssh]

[^vssh]: Vagrant waits for all devices to become reachable via SSH before reporting them ready.

**netlab initial** starts with a device readiness check to ensure the lab devices are ready for configuration deployment. If you want to execute just this part of the process, use the `--ready` option.

## Initial Device Configurations

Initial device configurations are created from inventory data and templates in the `netsim/ansible/templates/initial` directory[^USER_INIT]. A device-specific configuration template is selected using the `network_device_type` or the `ansible_network_os` value (making IOSv and CSR 1000v templates identical). See [](../dev/config/deploy.md) for more details.

[^USER_INIT]: You can overwrite _netlab_ initial configuration templates with your own: store them in the `templates/initial` directory of the current directory or the `~/.netlab` directory. See [](../customize.md) for more information.

The following initial configuration parameters are supported:

* hostname
* interface IPv4 and IPv6 addresses
* unnumbered interfaces
* interface descriptions
* interface MAC addresses
* interface bandwidth (when supported by the device)

The initial configuration also includes LLDP running on all interfaces apart from the management interface (not configurable).

Default passwords and other default configuration parameters are supposed to be provided by the Vagrant boxes.

## Module Configurations

Module-specific device configurations are created from templates in the `netsim/ansible/templates/_module_` directory[^USER_MOD]. A device-specific configuration template is selected using the `netlab_device_type` or the `ansible_network_os` value. 

[^USER_MOD]: You can overwrite _netlab_ module-specific configuration templates with your own: store your templates in the `templates/_module_` directory of the current directory or the `~/.netlab` directory. See [](../customize.md) for more information.

More details: 

* [Module descriptions](../module-reference.md) contain list of supported model parameters.
* [](../dev/config/deploy.md) describes the details of template search process
* [](../dev/device-features.md) contains the configuration template guidelines.
* You can [replace _netlab_ device configuration templates with your own](customize-templates)

(netlab-initial-custom)=
## Custom Deployment Templates

[Custom deployment templates](custom-config) are specified in **config** group- or node parameter. `initial-config.ansible` playbook used by **netlab initial** command tries to find the target configuration template in user-  and system (`netsim/extra`) directories and uses node name, `netlab_device_type` and `ansible_network_os` Ansible variables to allow you to create numerous device-specific configuration templates.

You'll find more details in _[](custom-config)_ and _[](dev-find-custom)_ documentation.

## Limiting the Scope of Configuration Deployments

The **netlab initial** command deploys all initial device configurations when started without additional parameters. To control the deployment of initial configurations:

* use the `-i` flag to deploy initial device configurations. 
* use the `-m` flag to deploy module-specific configurations. 
* use the `-m` flag followed by a module name (example: `-m ospf -m bgp`) to deploy device configuration for specific modules. You can use the `-m` flag multiple times.
* use the `-c` flag to deploy custom configuration templates. 

All unrecognized parameters are passed to the internal `initial-config.ansible` Ansible playbook. You can use **ansible-playbook** CLI parameters to modify the configuration deployment, for example:

* `-l` parameter to deploy device configurations on a subset of devices.
* `-C` parameter to run the Ansible playbook in dry-run mode. Combine it with the `-v` parameter to see the configuration changes that would be deployed[^vx]

[^vx]: The Ansible playbook uses **vtysh** on Cumulus Linux or FRR to deploy the FRR-related configuration changes from a file. The dry run will not display the configuration changes.

## Debugging Initial Configurations

* Use the `-o` flag to create device configurations without deploying them. The optional value of `-o` parameter specifies the output directory name (default: `config`)
* To display device configurations without deploying them, use `-v --tags test` flags (a bogus playbook tag turns off configuration deployment).
