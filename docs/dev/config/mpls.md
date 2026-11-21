(dev-mpls)=
# MPLS-Related Configuration Templates

This document describes how to create configuration templates for the **[mpls](module-mpls)** configuration module to implement LDP, MPLS/VPN, 6PE, or BGP-LU.

## Enabling MPLS Support on a Device

To enable MPLS features on a device, add the `mpls` dictionary to the device YAML file (`netsim/devices/<device>.yml`). Enable individual features within that file, for example:

```yaml
mpls:
  vpn: true
```

(dev-mpls-features)=
## Device Features

You can use the following **features.mpls** [device features](dev-device-features) to specify which MPLS features your configuration templates implement. The **mpls** module reports an error when a node uses a feature or an attribute that its device does not support.

* **ldp** -- The templates configure LDP ([more details](dev-mpls-ldp)). Set it to **true** or to a dictionary of supported optional LDP attributes:

  * **ldp.explicit_null** -- The LDP template implements the **ldp.explicit_null** attribute
  * **ldp.igp_sync** -- The device (or its IGP templates) implements the **ldp.igp_sync** attribute

* **bgp** -- The templates configure BGP Labeled Unicast. Set it to **true** to support IPv4 and IPv6 BGP-LU, or to a dictionary of supported address families and optional BGP-LU attributes:

  * **bgp.ipv4** and **bgp.ipv6** -- The templates configure IPv4/IPv6 BGP-LU. You have to specify the supported address families when using the dictionary format.
  * **bgp.explicit_null** -- The BGP-LU template implements the **mpls.bgp.explicit_null** attribute
  * **bgp.disable_unlabeled** -- The BGP-LU template implements the **mpls.bgp.disable_unlabeled** attribute

* **vpn** -- The templates configure MPLS/VPN. Set it to **true** to support VPNv4 and VPNv6 address families or to a dictionary of supported address families (for example, `vpn.ipv4: true`)
* **6pe** -- The templates configure 6PE ([more details](dev-mpls-6pe))
* **csc** -- The templates configure LDP on VRF interfaces (MPLS Carrier Supporting Carrier)
* **caveats.core** -- The anchor of the [caveats](platform-caveats) section describing the MPLS limitations (used only to add caveat links to the [supported features tables](dev-features-tables))

## Template Architecture

The MPLS configuration uses a two-tier template structure. The templates should be stored in the `netsim/ansible/templates/mpls/` directory. Feature-specific templates can also be stored within the `netsim/ansible/templates/mpls/<platform>` directory (example: IOS XR).

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

## Testing

The MPLS integration tests are in the `tests/integration/mpls` directory:

* `01-ldp-p` and `02-ldp-pe` -- LDP on P- and PE-devices ([more details](dev-mpls-ldp))
* `10-vpn-connected` to `15-vpnv4-rr` -- VPNv4 MPLS/VPN ([more details](dev-mpls-vpn))
* `20-vpnv6-connected` and `25-vpnv6-rr` -- VPNv6 MPLS/VPN
* `30-6pe-connected` and `31-6pe-rr` -- 6PE ([more details](dev-mpls-6pe))

The `tests/coverage/errors/mpls-optional-attr.yml` coverage test checks the error messages generated when a node uses optional LDP/BGP-LU attributes its device does not support.

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Configuring MPLS Features

   mpls-ldp.md
   mpls-vpn.md
   mpls-6pe.md
```
