(plugin-vrrp-version)=
# VRRP version

The **vrrp.version** plugin enables the configuration of the VRRP protocol version, specifically VRRPv2 (obsolete).
Netlab only supports VRRPv3 by default

The current version only supports configuring the VRRP version globally for each node, not at a per-interface level

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | VRRPV2 | Notes
| ------------------- | :----: | 
| Dell OS10           |   ✅   | VRRPv2 is the default on OS10

## Example config
```
module: [gateway]
plugin: [vrrp.version]  

gateway.vrrp.version: 2 # Optional, this is the assumed default when using this plugin
```