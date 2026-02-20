(dev-mpls)=
# MPLS-Related Configuration Templates

This document describes how to create configuration templates for the **[mpls](module-mpls)** configuration module to implement LDP, MPLS/VPN, 6PE, or BGP-LU.

## Enabling MPLS/VPN Support on a Device

To enable MPLS features on a device, add the `mpls` dictionary to the device YAML file (`netsim/devices/<device>.yml`). Enable individual features within that file, for example:

```yaml
mpls:
  vpn: true
```

## Template Architecture

The MPLS configuration uses a two-tier template structure. The templates should be stored in the `netsim/ansible/templates/mpls/` directory. Feature-specific templates can also be stored within the `netsim/ansible/templates/mpls/<platform>` directory (example: IOS XR)

### Main MPLS Template

The `<platform>.j2` template (e.g., `eos.j2`) includes templates for MPLS sub-features based on **ldp** or **mpls** node variables:

```
{% if ldp is defined %}
{%   include '<platform>.ldp.j2' +%}
{% endif %}
{% if mpls.bgp is defined %}
{%   include '<platform>.bgp-lu.j2' +%}
{% endif %}
{% if mpls.vpn is defined %}
{%   include '<platform>.mplsvpn.j2' +%}
{% endif %}
{% if mpls['6pe'] is defined %}
{%   include '<platform>.6pe.j2' +%}
{% endif %}
```

```{tip}
The `<platform>` is the value of the `netlab_device_type` or `ansible_network_os` variable.
```

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Configuring MPLS Features

   mpls-ldp.md
   mpls-vpn.md
```
