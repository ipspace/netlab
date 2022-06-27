import typing, netaddr
from box import Box
from netsim import common
from netsim import api
from netsim import data

"""
Adds a custom bgp.{allowas_in,as_override} as link->node (interface) attribute
"""
def init(topology: Box) -> None:
    topology.defaults.bgp.attributes.interface.append('allowas_in')
    topology.defaults.bgp.attributes.interface.append('as_override')
    topology.defaults.bgp.attributes.link.append('password')

def pre_link_transform(topology: Box) -> None:
    # Error if BGP module is not loaded
    if not 'bgp' in topology.module:
        common.error(
            f'BGP Module is not loaded.',
            common.IncorrectValue,
            'ebgp_utils')
    # Validate custom attributes
    # Iterate over node[x].interfaces
    for link in topology.links:
        for intf in link.interfaces:
            if 'bgp' in intf:
                # as_override shall be bool
                data.must_be_bool(parent=intf.bgp,key='as_override', path=f'links[{link.linkindex}].{intf.node}.bgp')
                # allowas_in shall be int (force 1 if True)
                data.must_be_int(parent=intf.bgp,key='allowas_in', path=f'links[{link.linkindex}].{intf.node}.bgp', true_value=1, min_value=1, max_value=10)
        if 'bgp' in link:
            # password
            data.must_be_string(parent=link.bgp,key='password', path=f'links[{link.linkindex}].bgp')

def post_transform(topology: Box) -> None:
    config_name = api.get_config_name(globals())
    # Iterate over node[x].interfaces
    for n, ndata in topology.nodes.items():
        for intf in ndata.interfaces:
            #print("LINK START *******************")
            #print(intf)
            #print("LINK END   *******************")
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
