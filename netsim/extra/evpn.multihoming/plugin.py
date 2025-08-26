# Support for EVPN Ethernet Segments

#### side notes: on platform supporting both ESI-LAG and MC-LAG, must remove _mclag flag from lag interfaces, to avoid mclag config

import netaddr
from box import Box

from netsim import api, data
from netsim.augment import devices
from netsim.modules import _dataplane
from netsim.utils import log

_config_name = 'evpn.multihoming'
_requires = [ 'evpn' ]
_execute_after = [ 'evpn', 'lag' ]

# Ethernet Segments can be supported on LAG and "physical interfaces", which means the following types for netlab
_es_supported_on = [ 'lag', # LAG interfaces
                     'p2p', 'stub', 'lan'  # other physical interfaces
                    ]

ID_SET = 'esi_auto_id'
_auto_segments = {}

# structure used to report used ESI, to generate user warnings
_esi_stats = data.get_empty_box()

# transform a 10-bytes ESI value to int
#  consider only the first most significant 5 bytes (excluding initial 00) - see below
def _esi_10bytes_to_int(esi: str) -> int:
    esi_l = esi.split(":")
    esi_hex = "".join(esi_l[1:6])
    return int(esi_hex, 16)

# Collect any user defined ethernet_segments.xxx.id values (as int) and initialize ID generator
#  we prefer to use as auto generated IDs only 5 bytes, to have unique ES-Import target and LACP System ID (starting with 02),
#  so we will consider only the first most significant 5 bytes (excluding initial 00)
def _init_es_id_generator(topology: Box) -> None:
    _dataplane.create_id_set(ID_SET)
    used_esi = set()
    for es, esdata in topology.get('ethernet_segments', {}).items():
        if 'id' in esdata:
            used_esi.add(_esi_10bytes_to_int(esdata.id))
    _dataplane.extend_id_set(ID_SET, used_esi)
    # we cannot start from 0
    _dataplane.set_id_counter(ID_SET, 1)

def _generate_esi_and_lag_unique_id() -> tuple:
    # 00 02 . 5 bytes value taken from id . 00 00 00
    next_id = _dataplane.get_next_id(ID_SET)
    esi_id_hex = "0002{:010x}000000".format(next_id)
    lacp_sys_id = "02{:010x}".format(next_id)
    return (
            ':'.join(a+b for a,b in zip(esi_id_hex[::2], esi_id_hex[1::2])),
            str(netaddr.EUI(lacp_sys_id, dialect = netaddr.mac_unix_expanded))
        )

def _generate_es_struct(esname: str) -> dict:
    global _auto_segments
    unique_ids = _generate_esi_and_lag_unique_id()
    _auto_segments[esname] = {
        'id': unique_ids[0],
        '_lacp_system_id': unique_ids[1],
    }
    return _auto_segments[esname]

def _update_esi_stats(node: Box, interface: Box, esi_name: str, esi_data: dict) -> None:
    global _esi_stats
    if log.debug_active('plugin'):
        print(f"evpn.multihoming: CALLED ESI STATS {node.name} {interface.ifname} {esi_name} {esi_data}")
    
    # increment usage data
    data.append_to_list(_esi_stats.esi_reference,esi_name,f"{node.name}->{interface.ifname}")

    # handle ESI-LAG case
    if interface.type == 'lag' and interface.get('lag.lacp_system_id',False):
        lacp_sys_id = interface.lag.lacp_system_id
        _esi_stats.esi_lacp_id[esi_name][lacp_sys_id] = True
        data.append_to_list(_esi_stats.esi_lacp_id_info[esi_name],lacp_sys_id,f"{node.name}->{interface.ifname}")
    return

def _generate_esi_warnings() -> None:
    global _esi_stats
    # ESI used only once
    for esi_name, esi_use in _esi_stats.esi_reference.items():
        if len(esi_use) == 1:
            log.warning(
                text=f'EVPN Ethernet Segment "{esi_name}" seems to be used only once ({esi_use[0]})',
                module=_config_name,
                flag='evpn_mh_segment_used_once',
                more_hints=[ f'This could be due to a typo on Ethernet Segment name on the interface' ],
                )
    # ESI LAG LACP mismatch
    for esi_name, esi_lacp_ids in _esi_stats.esi_lacp_id.items():
        if len(esi_lacp_ids) > 1:
            mismatch_list = []
            for m in list(esi_lacp_ids):
                found_interfaces=",".join(_esi_stats.esi_lacp_id_info[esi_name][m])
                mismatch_list.append("[{}]->[{}]".format(m, found_interfaces))
            mismatch_txt = ", ".join(mismatch_list)
            log.warning(
                text=f'EVPN ESI-LAG "{esi_name}" LACP mismatch. Found: {mismatch_txt}',
                module=_config_name,
                flag='evpn_mh_lacp_mismatch',
                )
    return

def _unsupported_device_checks(node: Box) -> None:
    for intf in node.get('interfaces',[]):
        if intf.get('evpn.es', False):
            log.error(
                f'Node {node.name}({node.device}) does not support EVPN Multihoming'
                f' (found "evpn.es" attribute on interface {intf.ifname})',
                category=log.IncorrectAttr,
                module=_config_name)
            return

def _es_interface_attribute_validation(topology: Box, node: Box, intf: Box) -> bool:
    global _config_name
    features = devices.get_device_features(node,topology.defaults)
    intf_es = intf.evpn.es
    intf_es_data = node.evpn.ethernet_segments[intf_es]
    # Check for interface type support
    if intf_es and intf.type not in _es_supported_on:
        log.error(
            f'EVPN Ethernet Segment is supported only on LAG or "physical" interfaces '
            f'(found on: Node {node.name}({node.device}) - interface {intf.ifname} ({intf.type}))',
            category=log.IncorrectAttr,
            module=_config_name)
        return False
    # Check for explicit lag support
    if intf.type == 'lag' and not features.get('evpn.multihoming.lag', False):
        log.error(
            f'Node {node.name}({node.device}) does not support EVPN Ethernet Segment on LAG interfaces (found on: {intf.ifname})',
            category=log.IncorrectAttr,
            module=_config_name)
        return False
    # Check for other interface support (except lag)
    if intf.type in list(set(_es_supported_on) - set(['lag'])) and not features.get('evpn.multihoming.interface', False):
        log.error(
            f'Node {node.name}({node.device}) does not support EVPN Ethernet Segment on "physical" interfaces (found on: {intf.ifname})',
            category=log.IncorrectAttr,
            module=_config_name)
        return False
    # ES data: if none of auto or id value is specified, trigger error
    if intf_es_data is None or not (intf_es_data.get('auto',False) or intf_es_data.get('id',False)):
        log.error(
            f'Node {node.name}({node.device}) no valid EVPN Ethernet Segment Identifier configuration for {intf_es} (on interface {intf.ifname})',
            category=log.IncorrectAttr,
            module=_config_name)
        return False
    # ESI-LAG **requires** a manually assigned LACP System ID (unless we auto generate it)
    if intf.type == 'lag' and not intf.get('lag.lacp_system_id',False):
        log.error(
            f'Node {node.name}({node.device}) cannot use ESI-LAG interface without "lacp_system_id" ({intf.ifname})',
            category=log.IncorrectAttr,
            module=_config_name)
        return False
    # ES data: if auto value, and not lacp system id is defined (or not lag or not supported), trigger an error
    if intf_es_data.get('auto',False):
        if intf.type != 'lag':
            log.error(
                f'Node {node.name}({node.device}) cannot use auto ESI on non-LAG interface ({intf.ifname})',
                category=log.IncorrectAttr,
                module=_config_name)
            return False
        if not features.get('evpn.multihoming.esi_auto', False):
            log.error(
                f'Node {node.name}({node.device}) cannot use auto ESI on interface {intf.ifname} - auto generation not supported.',
                category=log.IncorrectAttr,
                module=_config_name)
            return False
    return True

def post_transform(topology: Box) -> None:
    global _config_name
    global _auto_segments
    global _esi_stats
    _init_es_id_generator(topology)
    for node in topology.nodes.values():
        if not 'evpn' in node.module: continue
        features = devices.get_device_features(node,topology.defaults)
        es_supported = 'evpn.multihoming' in features
        if not es_supported:
            _unsupported_device_checks(node)
            continue
        # Load Ethernet Segments data and expand it with auto segments
        es_data = node.evpn.ethernet_segments
        es_data.update(_auto_segments)
        for intf in node.get('interfaces',[]):
            intf_es = intf.get('evpn.es', '')
            if not intf_es: continue
            # check for unreferenced ESI, and auto generate values
            if intf_es not in es_data:
                intf_es_data = _generate_es_struct(intf_es)
                if log.debug_active('plugin'):
                    print(f'evpn.multihoming: Found interface ESI definition without reference: '
                          f'{intf_es} ({node.name}->{intf.ifname}): creating structure. [{intf_es_data}]')
                es_data.update({ intf_es: intf_es_data })
            # If LAG, auto generated ESI-ID and LACP-System-ID are not present, use also auto generated LACP ID
            if intf.type == 'lag' and not intf.get('lag.lacp_system_id',False) and '_lacp_system_id' in es_data[intf_es]:
                intf.lag.lacp_system_id = es_data[intf_es]._lacp_system_id
            # Error Validation checks - exit in case of errors
            if not _es_interface_attribute_validation(topology, node, intf): return
            # Update interface attributes
            intf_es_data = es_data[intf_es]
            # if interface is _mlag, ESI-LAG have the precedence: pop _mlag
            if intf.type == 'lag' and '_mlag' in intf.lag:
                intf.lag.pop('_mlag')
            intf.evpn._esi = intf_es_data
            _update_esi_stats(node, intf, intf_es, intf_es_data)
        api.node_config(node,_config_name)
    # additional "global" warnings:
    _generate_esi_warnings()
    return
