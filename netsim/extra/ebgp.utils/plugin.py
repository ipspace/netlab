import typing, netaddr
from box import Box
from netsim import common
from netsim import api
from netsim import data

"""
Adds a custom bgp.{allowas_in,as_override,default_originate} as link->node (interface) attribute
"""
def init(topology: Box) -> None:
    attr = topology.defaults.bgp.attributes
    attr.interface.allowas_in = { 'type': 'int', 'true_value': 1, 'min_value': 1, 'max_value': 10 }
    attr.interface.as_override = 'bool'
    attr.interface.default_originate = 'bool'
    attr.link.password = 'str'

def pre_link_transform(topology: Box) -> None:
    # Error if BGP module is not loaded
    if not 'bgp' in topology.module:
        common.error(
            f'BGP Module is not loaded.',
            common.IncorrectValue,
            'ebgp_utils')

def post_transform(topology: Box) -> None:
    config_name = api.get_config_name(globals())
    # Iterate over node[x].interfaces
    for n, ndata in topology.nodes.items():
        for intf in ndata.interfaces:
            #print("LINK START *******************")
            #print(intf)
            #print("LINK END   *******************")
            # Handle as_override
            as_override = data.get_from_box(intf, 'bgp.as_override')
            if as_override:
                # Report the parameter on the BGP session, based on ifindex
                for neigh in ndata.get('bgp', {}).get('neighbors', []):
                    if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                        neigh.as_override = as_override
                # Report the parameter on the BGP session (for VRF), based on ifindex
                if 'vrf' in intf:
                    for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
                        if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                            neigh.as_override = as_override
                api.node_config(ndata,config_name)
            # Handle allowas_in
            allowas_in = data.get_from_box(intf, 'bgp.allowas_in')
            if allowas_in:
                # Report the parameter on the BGP session, based on ifindex
                for neigh in ndata.get('bgp', {}).get('neighbors', []):
                    if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                        neigh.allowas_in = int(allowas_in)
                # Report the parameter on the BGP session (for VRF), based on ifindex
                if 'vrf' in intf:
                    for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
                        if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                            neigh.allowas_in = int(allowas_in)
                api.node_config(ndata,config_name)
            # Handle default_originate
            default_originate = data.get_from_box(intf, 'bgp.default_originate')
            if default_originate:
                # Report the parameter on the BGP session, based on ifindex
                for neigh in ndata.get('bgp', {}).get('neighbors', []):
                    if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                        neigh.default_originate = default_originate
                # Report the parameter on the BGP session (for VRF), based on ifindex
                if 'vrf' in intf:
                    for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
                        if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                            neigh.default_originate = default_originate
                api.node_config(ndata,config_name)
            # Handle bgp_password
            bgp_password = data.get_from_box(intf, 'bgp.password')
            if bgp_password:
                # Report the parameter on the BGP session, based on ifindex
                for neigh in ndata.get('bgp', {}).get('neighbors', []):
                    if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                        neigh.password = bgp_password
                # Report the parameter on the BGP session (for VRF), based on ifindex
                if 'vrf' in intf:
                    for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
                        if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
                            neigh.password = bgp_password
                api.node_config(ndata,config_name)
