# Firewall Zone-Based Plugin
## Simple rules for now, only default policy supported initially

from netsim.utils import log
from netsim.augment import addressing, devices
from netsim import api,data
from box import Box
import netaddr

_config_name = 'firewall.zonebased'

def post_transform(topology: Box) -> None:
    global _config_name
    for node in topology.nodes.values():
        features = devices.get_device_features(node,topology.defaults)
        zbf_supported = 'firewall.zonebased' in features
        for intf in node.get('interfaces',[]):
            # if link has a firewall zone, apply extra config to this node
            fw_zone = intf.get('firewall.zone', '')
            if not zbf_supported and fw_zone:
                log.error( f"Node {node.name}({node.device}) does not support 'firewall.zone' used on {intf.name}",
                        category=log.IncorrectAttr,module=_config_name)
            elif fw_zone:
                # add zone to list of zones
                node.firewall.zonebased._zones[fw_zone] = {}
                # add config template
                api.node_config(node,_config_name)
        # now check that zones defined in rules are defined
        rule_idx = 0
        for def_rule in node.get('firewall.zonebased.default_rules', []):
            for z_direction in [ 'from_zone', 'to_zone' ]:
                z = def_rule[z_direction]
                if z not in node.firewall.zonebased._zones:
                    log.error( f"Node {node.name} does not have zone '{z}' defined in default zone rule '{rule_idx}' direction '{z_direction}'",
                            category=log.IncorrectAttr,module=_config_name)
            rule_idx = rule_idx + 1
    return
