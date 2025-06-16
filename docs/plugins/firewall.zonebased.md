(plugin-firewall-zonebased)=
# Zone-Based Firewall plugin

This plugin creates simple Zone-Based Firewall configuration for specific nodes.

For now, the plugin supports only default *zone to zone* rules, with `permit` or `deny` actions.

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | Default Policies |
| ------------------- | :--: |
| Fortinet FortiOS    |  ✅  |
| Juniper vSRX        |  ✅  |
| VyOS                |  ✅  |

## Using the Plugin

* Add `plugin: [ firewall.zonebased ]` to the lab topology.
* Include the **firewall.zonebased.default_rules** attribute in the firewall node
* Include the **firewall.zone** attribute in the firewall links/interfaces

### Supported attributes

The plugin adds the following attributes defined at node level:
* **firewall.zonebased.default_rules** (list) -- List of defaults *zone to zone* policies. Each item is a *dict* with the following attributes:
    * **from_zone** (id, mandatory) -- Policy Source Zone
    * **to_zone** (id, mandatory) -- Policy Destination Zone
    * **action** (string, mandatory, one of `permit`, `deny`) -- Policy Action

Additional interface level attributes:
* **firewall.zone** (id) -- the firewall zone for this firewall interface

## Example

```

plugin: [ firewall.zonebased ]

nodes:
  fw:
    firewall.zonebased:
      default_rules:
      - from_zone: trusted
        to_zone: trusted
        action: permit
      - from_zone: trusted
        to_zone: untrusted
        action: permit
  h1:
  h2:

links:
- fw:
    firewall.zone: trusted
  h1:
- fw:
    firewall.zone: untrusted
  h2:
```
