from box import Box
from netsim.utils import log
from netsim import api

"""
Adds a custom bgp.{allowas_in,as_override,default_originate} as link->node (interface) attribute
Also adds tcp_ao attribute as global and per-link option
"""
def init(topology: Box) -> None:
    attr = topology.defaults.bgp.attributes
    attr.interface.allowas_in = { 'type': 'int', 'true_value': 1, 'min_value': 1, 'max_value': 10 }
    attr.interface.as_override = 'bool'
    attr.interface.default_originate = 'bool'
    attr.link.password = 'str'

    # Add global, node and per-link tcp_ao option (see RFC5925 - https://datatracker.ietf.org/doc/html/rfc5925)
    tcp_ao_algorithm = { 'type': 'str', 
                         'valid_values': ['aes-128-cmac','hmac-sha-1',''], 
                         'true_value': 'hmac-sha-1' } # Default to most common algo
    attr['global'].tcp_ao = tcp_ao_algorithm
    attr['node'].tcp_ao = tcp_ao_algorithm
    attr['link'].tcp_ao = tcp_ao_algorithm

def pre_link_transform(topology: Box) -> None:
    # Error if BGP module is not loaded
    if 'bgp' not in topology.module:
        log.error(
            'BGP Module is not loaded.',
            log.IncorrectValue,
            'ebgp_utils')

def post_transform(topology: Box) -> None:
    config_name = api.get_config_name(globals())
    # Iterate over node[x].interfaces
    for n, ndata in topology.nodes.items():
        for intf in ndata.interfaces:
            if not isinstance(intf.get('bgp',None),Box):
                continue
            #print("LINK START *******************")
            #print(intf)
            #print("LINK END   *******************")
            # Handle as_override
            as_override = intf.get('bgp.as_override',None)
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
            allowas_in = intf.get('bgp.allowas_in',None)
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
            default_originate = intf.get('bgp.default_originate',None)
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
            bgp_password = intf.get('bgp.password',None)
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
