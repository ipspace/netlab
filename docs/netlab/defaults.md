(netlab-defaults)=
# Display and Change System Defaults

**netlab defaults** provides a **sysctl**-like CLI interface for [netlab default settings](topo-defaults). You can use this command to:

* Display all defaults or a subset of defaults
* Display the source of each default setting
* Change a default setting in the specified default datastore.

```text
usage: netlab defaults [-h] [-r] [-s] [--directory] [--project] [--user] [--system]
                       [--package] [--yes] [--yaml]
                       [setting]

Manage netlab default settings

positional arguments:
  setting       Specify setting to set (with s=v) or display (can be a glob)

options:
  -h, --help    show this help message and exit
  -r, --regex   Display default settings matching a regular expression
  -s, --source  Display the source of the default setting
  --directory   Display or store settings from the current directory
  --project     Display or store settings from the current project defaults
  --user        Display or store settings from the user default file
  --system      Display or store settings from the system default file
  --package     Display settings included in netlab package
  --yes         Overwrite existing settings without a confirmation
  --yaml        Store changed defaults in expanded YAML format
```

## Displaying the Default Settings

You can display a subset of defaults (specify the **setting** parameter) or all defaults, either from all default sources, or from the source defined with the CLI flags `--directory` through `--package`. You can also inspect how various default sources change the default values with the `--source` flag.

For example, to display all defaults changed in the user default file (`~/.netlab.yml`), use **netlab defaults --user**:

```
$ netlab defaults --user
devices.arubacx.clab.image = vrnetlab/vr-aoscx:20240129204649 (user)
devices.csr.clab.image = vrnetlab/cisco_csr1000v:17.03.08 (user)
devices.nxos.clab.image = vrnetlab/vr-n9kv:9.3.10 (user)
devices.vptx.clab.image = vrnetlab/juniper_vjunosevolved:23.2R2.21-EVO (user)
devices.vsrx.clab.image = vrnetlab/juniper_vsrx:junos-vsrx-21.4R1.12 (user)
```

To display all sources of `devices.csr.clab.image` setting, use the **netlab defaults --source** command with the exact name of the parameter you're interested in:

```
$ netlab defaults --source devices.csr.clab.image
devices.csr.clab.image = vrnetlab/vr-csr:17.03.04 (netlab)
devices.csr.clab.image = vrnetlab/cisco_csr1000v:17.03.08 (user)
```

Specify a default prefix to display a subset of defaults. For example, to display Arista EOS EVPN features, use **devices.eos.features.evpn** parameter:

```
$ netlab defaults devices.eos.features.evpn
devices.eos.features.evpn.asymmetrical_irb = True
devices.eos.features.evpn.bundle = ['vlan_aware']
devices.eos.features.evpn.irb = True
```

You can also use glob expressions to select the parameters you want to display. For example, use `*clab.image*` to display all containerlab image settings:

```
$ netlab defaults '*clab.image'
daemons.bird.clab.image = netlab/bird:latest
daemons.dnsmasq.clab.image = netlab/dnsmasq:latest
devices.arubacx.clab.image = vrnetlab/vr-aoscx:20240129204649
devices.cat8000v.clab.image = vrnetlab/vr-c8000v:17.13.01a
devices.csr.clab.image = vrnetlab/cisco_csr1000v:17.03.08
devices.cumulus.clab.image = networkop/cx:4.4.0
devices.cumulus_nvue.clab.image = networkop/cx:5.3.0
devices.dellos10.clab.image = vrnetlab/vr-ftosv
devices.eos.clab.image = ceos:4.33.1F
...
```

Finally, use the `--regex` flag to specify the default settings as a regular expression, for example:

```
$ netlab defaults --regex 'evpn.*irb'
devices.arubacx.features.evpn.asymmetrical_irb = True
devices.arubacx.features.evpn.irb = True
devices.cumulus.features.evpn.asymmetrical_irb = True
devices.cumulus.features.evpn.irb = True
devices.cumulus_nvue.features.evpn.asymmetrical_irb = True
devices.cumulus_nvue.features.evpn.irb = True
devices.dellos10.features.evpn.asymmetrical_irb = True
devices.dellos10.features.evpn.irb = True
...
```

## Changing Default Values

Use **netlab defaults parameter=value** to change a default value. With no additional parameters, **netlab defaults** finds the most specific default datastore (from directory to user) and stores the modified parameter in that datastore.

For example, with no per-user default information, the **netlab defaults provider=clab** command stores the setting in the user defaults file:

```
$ netlab defaults provider=clab
The default setting provider is already set in netlab defaults
Do you want to change that setting in user defaults [y/n]: y
provider set to clab in /Users/me/.netlab.yml
```

You can specify the default datastore to modify with the `--directory` through `--system` parameter. For example, use **netlab defaults --directory device=eos** to set the default device for topologies in the current directory:

```
$ netlab defaults --directory device=eos
device set to eos in /Users/me/SomePath/topology-defaults.yml
```

The **netlab defaults** command accepts scalar and list values. You can use the following commands to inspect and modify the **bgp.warnings.igp_list** parameter:

```
$ netlab defaults bgp.warnings.igp_list
bgp.warnings.igp_list = ['ospf', 'eigrp', 'isis', 'ripv2']
$ netlab defaults bgp.warnings.igp_list='[ospf,isis]'
The default setting bgp.warnings.igp_list is already set in netlab defaults
Do you want to change that setting in user defaults [y/n]: y
bgp.warnings.igp_list set to ['ospf', 'isis'] in /Users/me/.netlab.yml
$ netlab defaults bgp.warnings.igp_list --source
bgp.warnings.igp_list = ['ospf', 'eigrp', 'isis', 'ripv2'] (netlab)
bgp.warnings.igp_list = ['ospf', 'isis'] (user)
```
