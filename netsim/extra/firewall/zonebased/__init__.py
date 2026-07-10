# Firewall Zone-Based Plugin
## Simple rules for now, only default policy supported initially

from box import Box

from netsim import api
from netsim.augment import devices
from netsim.utils import log

_config_name = 'firewall.zonebased'

def post_transform(topology: Box) -> None:
    global _config_name
    for node in topology.nodes.values():
        features = devices.get_device_features(node,topology.defaults)
        zbf_supported = 'firewall.zonebased' in features
        OK = True

        for intf in node.get('interfaces',[]):
            fw_zone = intf.get('firewall.zone', '')
            if not fw_zone:                                     # No zone defined on the interface, move on
                continue
            if not zbf_supported:                               # Not supported, print error and move on
                log.error( f"Node {node.name}({node.device}) does not support 'firewall.zone' used on {intf.name}",
                        category=log.IncorrectAttr,module=_config_name)
                OK = False
                continue

            node.firewall.zonebased._zones[fw_zone] = {}        # Add zone to the list of zones
            api.node_config(node,_config_name)                  # ... and remember we have to do extra config

        if not OK:                                              # Errors? Move on
            continue

        # now check that zones defined in rules are defined
        for rule_idx,def_rule in enumerate(node.get('firewall.zonebased.default_rules', [])):
            for z_direction in [ 'from_zone', 'to_zone' ]:
                z = def_rule[z_direction]
                if z not in node.firewall.zonebased._zones:
                    log.error( f"Node {node.name} does not have zone '{z}' used in firewall.zonebased.default_rules[{rule_idx}].{z_direction}",
                            category=log.IncorrectAttr,module=_config_name)
    return
