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

# Ethernet Segments can be supported on LAG and "physical interfaces", which means the following types for netlab
_es_supported_on = [ 'lag', # LAG interfaces
                     'p2p', 'stub', 'lan'  # other physical interfaces
                    ]

def post_transform(topology: Box) -> None:
    global _config_name
    for node in topology.nodes.values():
        if not 'evpn' in node.module: continue
        features = devices.get_device_features(node,topology.defaults)
        es_supported = 'evpn.es' in features
        if not es_supported: continue
        # Load Ethernet Segments data and expand it
        es_data = node.get('evpn.ethernet_segments', {})
        for intf in node.get('interfaces',[]):
            intf_es = intf.get('evpn.es', '')
            if not intf_es: continue
            if intf_es and intf.type not in _es_supported_on:
                log.error(
                    f'EVPN Ethernet Segment is supported only on LAG or "physical" interfaces '
                    f'(found on: Node {node.name}({node.device}) - interface {intf.ifname} ({intf.type}))',
                    category=log.IncorrectAttr,
                    module='evpn.es')
                return
            # Check for explicit lag support
            if intf.type == 'lag' and not features.get('evpn.es.lag', False):
                log.error(
                    f'Node {node.name}({node.device}) does not support EVPN Ethernet Segment on LAG interfaces (found on: {intf.ifname})',
                    category=log.IncorrectAttr,
                    module='evpn.es')
                return
            # Check for other interface support (except lag)
            if intf.type in list(set(_es_supported_on) - set(['lag'])) and not features.get('evpn.es.interface', False):
                log.error(
                    f'Node {node.name}({node.device}) does not support EVPN Ethernet Segment on "physical" interfaces (found on: {intf.ifname})',
                    category=log.IncorrectAttr,
                    module='evpn.es')
                return
            if intf_es not in es_data:
                log.error(
                    f'Node {node.name}({node.device}) invalid EVPN Ethernet Segment configured on interface {intf.ifname}',
                    category=log.IncorrectValue,
                    module='evpn.es')
                return
            intf_es_data = es_data[intf_es]
            # if none of auto or id value is specified, trigger error
            if intf_es_data is None or not (es_data[intf_es].get('auto',False) or es_data[intf_es].get('id',False)):
                log.error(
                    f'Node {node.name}({node.device}) no valid EVPN Ethernet Segment Identifier configuration for {intf_es} (on interface {intf.ifname})',
                    category=log.IncorrectAttr,
                    module='evpn.es')
                return
            # if auto value, and not lacp system id is defined (or not lag or not supported), trigger an error
            if es_data[intf_es].get('auto',False):
                if intf.type != 'lag':
                    log.error(
                        f'Node {node.name}({node.device}) cannot use auto ESI on non-LAG interface ({intf.ifname})',
                        category=log.IncorrectAttr,
                        module='evpn.es')
                    return
                if not intf.get('lag.lacp_system_id',False):
                    log.error(
                        f'Node {node.name}({node.device}) cannot use auto ESI on LAG interface without "lacp_system_id" ({intf.ifname})',
                        category=log.IncorrectAttr,
                        module='evpn.es')
                    return
                if not features.get('evpn.es.esi_auto', False):
                    log.error(
                        f'Node {node.name}({node.device}) cannot use auto ESI on interface {intf.ifname} - auto generation not supported.',
                        category=log.IncorrectAttr,
                        module='evpn.es')
                    return
            # if interface is _mlag, ESI-LAG have the precedence: pop _mlag
            if intf.type == 'lag' and '_mlag' in intf.lag:
                intf.lag.pop('_mlag')
            intf.evpn._esi = intf_es_data
        
        api.node_config(node,_config_name)
    return
