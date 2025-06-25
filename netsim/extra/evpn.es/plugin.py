# Support for EVPN Ethernet Segments

#### side notes: on platform supporting both ESI-LAG and MC-LAG, must remove _mclag flag from lag interfaces, to avoid mclag config

from netsim.utils import log
from netsim.augment import addressing, devices
from netsim import api,data
from box import Box
import netaddr

_config_name = 'evpn.es'
_requires = [ 'evpn' ]
_execute_after = [ 'evpn', 'lag' ]

def post_transform(topology: Box) -> None:
    global _config_name
    for node in topology.nodes.values():
        features = devices.get_device_features(node,topology.defaults)
        es_supported = 'evpn.es' in features
        if not es_supported: continue
        api.node_config(node,_config_name)
    return


"""
OLD CODE

          # Convert "esi: true" to auto-derived ESI value
          # depending on platform support, either platform auto-derivation or this manually generated ESI can be used.
          if i.lag.get('esi', False) is True:
            i.lag._esi_auto_derive = True
            i.lag._esi_manual = "00:{}:00:00:00".format(i.lag.lacp_system_id)
        elif i.lag.get('esi', False) and not features.lag.get('esi', False):
          log.error(f'Node {node.name}({node.device}) does not support ESI-LAG configured on interface {i.ifname}',
            category=log.IncorrectAttr,
            module='lag')

"""
