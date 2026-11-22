(dev-config-eigrp)=
# Configuring EIGRP

This document describes the device data model parameters used in EIGRP device configuration templates. Please see the [contributing new devices](dev-new-devices) document for a wider picture.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/ansible/templates/eigrp/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](dev-devices-ansible-vars) for more details).
* The EIGRP configuration is applied after the VLAN and routing configuration.
* _netlab_ does not support EIGRP in VRFs; the VRF interfaces are removed from the EIGRP configuration.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-eigrp-features)=
## Device Features

You can use the following **features.eigrp** [device features](dev-device-features) to specify which EIGRP features your configuration template implements:

* **ipv4**, **ipv6** -- Set these features to **false** if your device (or your template) cannot run EIGRP for IPv4 or IPv6; the **eigrp** module reports an error when such a device uses EIGRP with that address family. A device without these features is assumed to support EIGRP for IPv4 and IPv6.

(dev-eigrp-af)=
## Supporting Multiple Address Families

The **eigrp.af** variable contains a dictionary of address families configured on the device:

* **eigrp.af.ipv4** -- there is at least one interface on which you could run EIGRP for IPv4
* **eigrp.af.ipv6** -- there is at least one interface on which you could run EIGRP for IPv6

EIGRP for IPv4 and EIGRP for IPv6 are usually configured as separate routing processes.

(dev-eigrp-node)=
## Node Parameters

The **eigrp** module sets these parameters in the node **eigrp** dictionary:

* **as** (integer) -- The EIGRP AS number
* **router_id** (string) -- The EIGRP router ID
* **af** (dictionary) -- The EIGRP address families (see [](dev-eigrp-af))

(dev-eigrp-intf)=
## Interface Parameters

The **eigrp** module sets the **eigrp** dictionary on all interfaces on which the device should run EIGRP, including the loopback interface. Interfaces without the **eigrp** dictionary (layer-2 interfaces, external interfaces, VRF interfaces) should not be configured. Use **netlab_interfaces** (a list containing the loopback interface and the node **interfaces**) to configure the loopback and the physical interfaces in a single loop.

The **eigrp** interface dictionary contains the **passive** parameter (boolean, always present). Stub interfaces and the interfaces with the **eigrp.passive** link attribute are passive.

Configure EIGRP for an address family on an interface only when the interface has an address from that address family (**ipv4** or **ipv6** interface attribute) and the address family is in the **eigrp.af** dictionary. The **ipv4** attribute of an unnumbered IPv4 interface and the **ipv6** attribute of an LLA-only IPv6 interface are set to **true**.

This is how the Cisco IOS template configures EIGRP for IPv4 and IPv6:

```jinja
{% if eigrp.af.ipv4 is defined %}
router eigrp {{ eigrp.as }}
{% if eigrp.router_id is defined %}
 eigrp router-id {{ eigrp.router_id }}
{% endif %}
{% for l in netlab_interfaces|default([]) if 'eigrp' in l and 'ipv4' in l  and l.ipv4 is string %}
 network {{ l.ipv4|ansible.utils.ipaddr('address') }} 0.0.0.0
{% endfor %}
{% for l in interfaces|default([]) if 'eigrp' in l and l.eigrp.passive %}
 passive-interface {{ l.ifname }}
{% endfor %}
!
{% endif %}
{% if eigrp.af.ipv6 is defined %}
ipv6 router eigrp {{ eigrp.as }}
{% if eigrp.router_id is defined %}
 eigrp router-id {{ eigrp.router_id }}
{% endif %}
{% for l in netlab_interfaces|default([]) if 'eigrp' in l and l.eigrp.passive %}
 passive-interface {{ l.ifname }}
{% endfor %}
!
{% for l in netlab_interfaces|default([]) if 'eigrp' in l and 'ipv6' in l %}
interface {{ l.ifname }}
 ipv6 eigrp {{ eigrp.as }}
!
{% endfor %}
{% endif %}
```

## Integration Tests

The EIGRP integration tests are in the `tests/integration/eigrp` directory:

* `01-eigrp-ipv4.yml` -- EIGRP for IPv4
* `02-eigrp-ipv6.yml` -- EIGRP for IPv6
