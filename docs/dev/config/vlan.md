# Configuring VLANs

This document describes the device data model parameters one should consider when creating a VLAN configuration template. For a wider picture, please see [contributing new devices](../devices.md) document.

This document assumes you're using an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build device configuration, you'll find some guidance in [Using Ansible Configuration Modules](ospf-ansible-config) section of OSPF implementation guide.

VLAN node- and interface data model contains enough information to implement VLANs on a wide variety of platforms, including:

* Switch-like platforms that use a VLAN database, VLAN trunks on physical interfaces, and VLAN/SVI interfaces (example: Dell OS10). Set **vlan.model** attribute to **switch**.
* Router-like platforms that use bridge groups, VLAN subinterfaces on physical interfaces, and BVI/IRB interfaces (example: Cisco IOSv, Nokia SR Linux, Mikrotik RouterOS). Set **vlan.model** attribute to **router**.
* Switch-like platforms that support both routed and switched ports, or a hybrid approach where some ports can be routed using VLAN subinterfaces, while other ports could be connected to the internal L2/L3 switch (example: Arista EOS, VyOS). Set **vlan.model** attribute to **l3-switch**.

You might want to use the VLAN integration test cases in `tests/integration/vlan` directory to test your implementation.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/vlan/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## VLAN Principles

Data model:

* VLANs are defined in node-level **vlans** dictionary. Use this dictionary to get VLAN ID (802.1q tag), bridge group ID, and VNI.
* Interface VLAN parameters are specified in interface **vlan** dictionary. Do not use any other parameter (for example, **vlan_name**).
* VLAN interfaces or routed VLAN subinterface are created as needed on platforms that support them. These interfaces have **virtual_interface** set to *True*; you can further classify them with the **type** attribute:

  * VLAN/SVI/BVI interface have **type** set to *svi*
  * Routed VLAN subinterfaces have **type** set to ‌*vlan_member*

VLAN-related interfaces are included in the **node.interfaces** list and are thus best configured in *initial* configuration template[^FC]. The other VLAN-related parameters should be configured in `netsim/templates/vlan/<nos>.j2` template (or corresponding Ansible task list).

[^FC]: You might have to include further VLAN-related configuration in that configuration template to make them work.

## Device Features

You have to specify VLAN-related capabilities of your device in `devices.<device>.features.vlan` dictionary in `topology-defaults.yml`. You can set the following parameters:

* **model** -- describes the way the device implements VLAN interfaces. Valid values are **router**, **switch** or **l3-switch**. See the introductory section of this document for more details.
* **svi_interface_name** -- a template for the VLAN/SVI/BVI interface name. You can use `{vlan}` or `{bvi}` within this string to set the interface name based on VLAN ID or bridge group.
* **subif_name** -- name of VLAN subinterfaces for **router** platforms or routed VLAN subinterface name for **l3-switch** platforms. Use `{ifname}` to get the parent interface name, `{subif_index}` to get subinterface ID[^SID], and `{vlan.access_id}` to get the VLAN tag[^SUBIF].
* **first_subif_id** -- subinterface ID of the first subinterface in case your platform uses unusual subinterface names. Defaults to 1.
* **mixed_trunk** -- set to *True* when a platform supports a mix of bridged and routed VLANs on a trunk interface, regardless of the platform type -- applicable to **router** and **l3-switch** platforms.
* **native_routed** -- set to *True* when a platform supports routed native VLAN on a trunk interface (effectively untagged IP + VLAN trunk) -- applicable to **router** and **l3-switch** platforms.

[^SID]: A counter starting at **first_subif_id**.

[^SUBIF]: You can also use any other attribute from the parent interface, or attributes from the current interface (like `vlan.access_id`) that are not defined on the parent interface.

The following VLAN features have been defined for Cisco IOSv, Arista EOS, VyOS, Mikrotik RouterOS and Dell OS10:

```
devices:
  iosv:
    features:
      vlan:
        model: router
        svi_interface_name: BVI{bvi}
        subif_name: "{ifname}.{subif_index}"
  eos:
    features:
      vlan:
        model: l3-switch
        svi_interface_name: Vlan{vlan}
        subif_name: "{ifname}.{subif_index}"
  srlinux:
    features:
      vlan:
        model: router
        svi_interface_name: "vlan{vlan}"
        subif_name: "{ifname}.{subif_index}"
  vyos:
    features:
      vlan:
        model: l3-switch
        svi_interface_name: "br0.{vlan}"
        subif_name: "{ifname}.{vlan.access_id}"
  dellos10:
    features:
      vlan:
        model: switch
        svi_interface_name: vlan{vlan}
  routeros:
    features:
      vlan:
        model: router
        svi_interface_name: bridge{vlan}
        subif_name: "{ifname}-{vlan.access_id}"
```

**Notes:**
* Cisco IOSv is a router and uses BVI (bridge group) interface and per-VLAN subinterfaces.
* Arista EOS is a switch and uses VLAN interfaces. It also supports routed VLAN subinterfaces.
* VyOS uses a VLAN-aware Linux bridge and creates VLAN interfaces by appending VLAN ID to bridge name - so it behaves like a switch. It also supports routed VLAN subinterfaces.
* Dell OS10 is a switch and uses VLAN interfaces. As specified above, it does not support routed VLAN subinterfaces.
* Mikrotik RouterOS is a router and uses bridge interface and per-VLAN subinterfaces.

## Interface Configuration

It's easiest to create VLAN interfaces and subinterfaces in the `netsim/templates/initial/<nos>.j2` configuration template. Use **virtual_interface** attribute to skip configuration parameters that apply only to physical interfaces. For example, you cannot configure **switchport** or **mac-address** on an Arista EOS VLAN interface.

Arista EOS interface configuration template:
```
{% for l in interfaces|default([]) %}
interface {{ l.ifname }}
 no shutdown
{% if l.virtual_interface is not defined %}
 no switchport
 mac-address {{ '52dc.cafe.%02d%02d' % ( id,l.ifindex ) }}
{% endif %}
{% endfor %}
```

Some operating systems (example: Cisco IOS) don't want to create VLAN or BVI interface unless you have already configured the corresponding VLAN or bridge-group.

Cisco IOS initial configuration template thus checks for presence of **vlans** dictionary:

```
{% if vlans is defined %}
{% include 'ios.vlan.j2' %}
{% endif %}
```

Cisco IOS initial VLAN configuration creates the necessary bridge groups. VLANs are assigned to bridge groups during the VLAN configuration process.

```
bridge irb
!
{% for vname,vdata in vlans.items() %}
bridge {{ vdata.bridge_group }} protocol ieee
bridge {{ vdata.bridge_group }} route ip
!
{% endfor +%}
```

## VLAN Database Configuration

Use the **vlans** node dictionary to create a list of VLANs used by a device. Each VLAN within the **vlans** dictionary has at least these attributes

* **id** -- 802.1q tag
* **vni** -- VXLAN VNI
* **bridge_group** -- VLAN-specific bridge group within the node.

Switch-like devices usually need a VLAN database. The following template configures it on Arista EOS:

```
{% if vlans is defined %}
{%   for vname,vdata in vlans.items() %}
vlan {{ vdata.id }}
 name {{ vname }}
!
{%   endfor +%}
{% endif %}
```

## Interface VLAN Parameters

Based on the capabilities of your platform, you might have to configure:

* VLAN access interfaces
* VLAN trunks
* Native VLAN
* VLAN encapsulation on a VLAN- or routed subinterface

You can use the following interface VLAN parameters to configure VLANs:

* A trunk VLAN interface has **vlan.trunk_id** list that contains the list of VLANs on that trunk.
* A trunk VLAN interface might have a native VLAN. Its 802.1q tag is specified in **vlan.access_id** attribute, its name in **vlan.native** attribute. The native VLAN 802.1q tag is also included in **vlan.trunk_id**
* An access VLAN interface has **vlan.access_id** attribute that contains the 802.1 VLAN tag. You can also use **vlan.access** attribute to get VLAN name.
* A routed VLAN subinterface has VLAN 802.1q tag in **vlan.access_id** attribute. There is no **vlan.access** or **vlan.native** attribute.
* Use **type** to differentiate between a VLAN access physical interface and a routed VLAN subinterface -- routed subinterfaces have **type** set to *vlan_member*

### Switch-Like Platforms

Use the following logic to configure interface VLANs parameters on platforms that look like switches:

* Is **vlan.trunk_id** defined? ➜ trunk interface

	* Set interface mode to trunk
	* Set list of allowed VLANs from **vlan.trunk_id**
	* If **vlan.native** is defined, set native VLAN from **vlan.access_id**

* Else: Is **vlan.access_id** defined? ➜ access or routed subinterface

	* Is **type** equal to *vlan_member*? ➜ routed VLAN subinterface, set VLAN tag
	* Else: Access VLAN interface:

		* Set interface mode to access
		* Set access VLAN 802.1q tag from **vlan.access_id**

The following template implements that logic for Arista EOS:

```
{% for ifdata in interfaces if ifdata.vlan is defined %}
!
interface {{ ifdata.ifname }}
{%   if ifdata.vlan.trunk_id is defined %}
 switchport
 switchport mode trunk
 switchport trunk allowed vlan {{ ifdata.vlan.trunk_id|sort|join(",") }}
{%     if ifdata.vlan.native is defined %}
 switchport trunk native vlan {{ ifdata.vlan.access_id }}
{%     endif %}
{%   elif ifdata.vlan.access_id is defined %}
{%     if ifdata.type == 'vlan_member' %}
 encapsulation dot1q vlan {{ ifdata.vlan.access_id }}
{%     else %}
 switchport
 switchport access vlan {{ ifdata.vlan.access_id }}
{%     endif %}
{%   endif %}
{% endfor +%}
```

Alternatively, you could check for:

* **vlan.trunk_id** ➜ trunk interface
* **vlan.access** ➜ access interface
* **vlan.access_id** but no **vlan.access** ➜ routed subinterface

### Router-Like Platforms

Router-like platforms implement VLANs by connecting physical interfaces or VLAN subinterfaces to bridge domains (groups). VLAN subinterfaces are created for every VLAN in a VLAN trunk; interface **type** for VLAN subinterfaces is set to *vlan_member* regardless of whether the VLAN is routed or bridged.

Configuring VLAN interface parameters on a router-like platform is even easier than doing it on a switch-like platform:

* If the VLAN name is specified (**vlan.access** or **vlan.native**), find the **bridge_group** from the VLAN database. Configure bridge group on the interface to connect the VLAN subinterface or access interface to the VLAN-specific bridge group.
* When configuring a VLAN subinterface (**type** == *vlan_member*), configure interface VLAN encapsulation using **vlan.access_id** parameter.

The following template configures VLAN interface parameters on Cisco IOS:

```
{% for ifdata in interfaces if ifdata.vlan is defined %}
!
interface {{ ifdata.ifname }}
{% if ifdata.type == 'vlan_member' and ifdata.vlan.access_id is defined %}
 encapsulation dot1Q {{ ifdata.vlan.access_id }}
{% endif %}
{% if ifdata.vlan.access is defined %}
 bridge-group {{ vlans[ifdata.vlan.access].bridge_group }}
{% endif %}
{% if ifdata.vlan.native is defined %}
 bridge-group {{ vlans[ifdata.vlan.native].bridge_group }}
{% endif %}
{% endfor %}
```