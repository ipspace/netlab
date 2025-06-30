(dev-config-ospf-areas)=
# Configuring OSPF Areas

This document describes the device data model parameters one should consider when creating a configuration template for OSPF areas. For a wider picture, please see the [](dev-new-devices) document.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Read This First

* OSPF areas are implemented in [](plugin-ospf-areas). You have to implement them for OSPFv2 and OSPFv3 (depending on what OSPF configuration your device supports).
* The device configuration templates should be stored in `netsim/extra/ospf.areas/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable.
* The support for OSPF areas is enabled with the **ospf.areas** [device feature](dev-device-features) in `netsim/extra/ospf.areas/defaults.yml`
* Setting a device **ospf.areas** feature to True means "I implemented all parts of the data model".
* If your device does not support some of the area attributes (example: NSSA ranges), the **ospf.areas** feature value should be a dictionary. The dictionary keys should be the unimplemented attributes, and their values should be the warning messages displayed when someone uses those attributes with your device.

## Adjustments to the Data Model

The data model closely follows the one defined in the [plugin documentation](plugin-ospf-areas). The areas are defined in the **areas** list in the global or VRF OSPF data. Each entry contains the documented attributes, with these exceptions:

* The value of the **area** attribute is always an IP address (for example, 0.0.0.1)
* The value of the **_area_int** attribute is an integer equivalent of the **area** attribute
* The **kind** attribute is always set. It's set to "regular" for non-stub/NSSA areas. There is no special provision for the backbone area.
* The **inter_area** attribute is always set (the default value is **True**)

Each entry in the range definition lists (**range**, **filter**, **external_range**, **external_filter**) contains **ipv4** and/or **ipv6** attributes (CIDR prefixes). An entry might contain both attributes or just one of them.

Additionally, the plugin sets the `_abr` attribute (value: True) in the OSPF data on the ABRs to allow you to configure ABR-specific features without counting the areas configured on the router.

## Configuration Guidelines

As you have to configure global and VRF instances of OSPFv2 and OSPFv3, it's best to define a macro that configures the areas (assuming the OSPFv2 and OSPFv3 configuration syntax are similar). Define two macros if you experience significant differences between OSPFv2 and OSPFv3 configuration syntax (you'll need them for global and VRF instances anyway).

The following code snippets are taken from the [FRRouting template](https://github.com/ipspace/netlab/blob/dev/netsim/extra/ospf.areas/frr.j2):

1. Define the macro:

   ```
   {% macro area_config(adata,af,abr) %}
   ```

   We're assuming that the calling code has already selected the OSPF instance and address family; this macro will only create the area definition commands. It needs the list of areas (`adata`), current address family (`af`), and whether the router has multiple areas (it's an ABR)

2. Use `adata.kind` to set the OSPF area type and `adata.inter_area` to decide whether to advertise type-3 LSAs into the area:

   ```
   {%   if adata.kind == 'stub' %}
     area {{ adata.area }} stub {% if not adata.inter_area %}no-summary{% endif +%}
   {%   elif adata.kind == 'nssa' %}
     area {{ adata.area }} nssa {% if not adata.inter_area %}no-summary{% endif +%}
   {%   endif %}
   ```

3. Sometimes you have to configure the origination of the default route into the NSSA area. You should configure that only on the ABRs:

   ```
   {%   if adata.kind == 'nssa' and abr and adata.default|default(false) %}
     area {{ adata.area }} nssa default-information-originate
   {%     endif %}
   ```

   Please note that the `adata.kind` value is always set, but `adata.default` is not, so you have to specify the default value for the latter.

4. If possible, set the cost of the default route advertised into stub/NSSA area (if specified):

   ```
   {%   if adata.kind in ['stub','nssa'] and adata.default.cost is defined and af == 'ipv4' %}
     area {{ adata.area }} default-cost {{ adata.default.cost }}
   {%   endif %}
   ```

   **Note:** FRR can specify the default cost only in OSPFv2

5. Configure area ranges for the current address family (but only on ABRs). You have to iterate over the four attributes and create the correct configuration commands:

```
{%     for range in adata.range|default([]) if range[af] is defined %}
  area {{ adata.area }} range {{ range[af] }}{{ range_cost(range) }}
{%     endfor %}
{%     for range in adata.filter|default([]) if range[af] is defined %}
  area {{ adata.area }} range {{ range[af] }} not-advertise
{%     endfor %}
{%     for range in adata.external_range|default([]) if range[af] is defined %}
  area {{ adata.area }} nssa range {{ range[af] }}{{ range_cost(range) }}
{%     endfor %}
{%     for range in adata.external_filter|default([]) if range[af] is defined %}
  area {{ adata.area }} nssa range {{ range[af] }} not-advertise
{%     endfor %}
```

5. Range cost is optional, so you have to check for the presence of that attribute. I decided to use a macro instead of doing it inline (twice):

   ```
   {% macro range_cost(range) %}
   {%   if range.cost is defined %} cost {{ range.cost }}{% endif %}
   {% endmacro %}
   ```

Next, you'll probably need a macro that selects the correct configuration context (OSPFv2/OSPFv3, global/VRF) and calls the **area_config** macro:

```
{% macro ospf_area_config(odata,vrf='') %}
{%   for af in ['ipv4','ipv6'] if odata.af[af] is defined %}
{%     set proto = 'ospf' if af == 'ipv4' else 'ospf6' %}
router {{ proto }}{% if vrf %} vrf {{ vrf }}{% endif +%}
{%     for adata in odata.areas %}
{{       area_config(adata,af,odata._abr|default(false)) -}}
{%     endfor %}
{%   endfor %}
{% endmacro %}
```

The macro iterates over IPv4 and IPv6 address families, creates the correct **router** command to select the configuration context, and then iterates over **ospf.areas** (please note that you might need an OSPF instance ID passed to that macro on some devices, see the [Arista EOS template](https://github.com/ipspace/netlab/blob/dev/netsim/extra/ospf.areas/eos.j2) for more details).

Finally, the top-level code calls the **ospf_area_config** macro if **ospf.areas** is defined in the node-level or VRF-level **ospf** dictionary:

```
{% if ospf.areas is defined %}
{{   ospf_area_config(ospf) }}
{% endif %}
{% if vrfs is defined %}
{%   for vname,vdata in vrfs.items() if vdata.ospf.areas is defined %}
{{     ospf_area_config(vdata.ospf,vname) }}
{%   endfor %}
{% endif %}
```

## Testing Your Implementation

The two integration tests you can use to test your device templates are:

* `tests/integration/ospf/ospfv2/40-area-parameters.yml` tests OSPFv2 implementation
* `tests/integration/ospf/ospfv3/40-area-parameters.yml` tests OSPFv3 implementation

See [using integration tests when developing initial device configuration templates](dev-config-initial-tests) for more details.
