
from box import Box

from netsim.augment import devices
from netsim.utils import log, strings


def pre_transform(topology: Box) -> None:

  D_FEATURES: dict = {}

  def get_features(node: Box) -> Box:
    device = node.device
    if device not in D_FEATURES:
      D_FEATURES[device] = devices.get_device_features(node,defaults)
    return D_FEATURES[device]

  defaults = topology.defaults
  for link in topology.get('links',[]):
    l_mtu = link.get('mtu',None)
    for intf in link.interfaces:
      mtu = intf.get('mtu',l_mtu)
      if not mtu:
        continue
      node = intf.node
      n_data = topology.nodes[node]
      max_mtu = get_features(n_data).get('initial.max_mtu',None)
      if not max_mtu:
        continue
      if max_mtu < mtu:
        warning = f"Device {n_data.device} (node {node}) does not support MTU {mtu}. " +\
                  "MTU on {o_name}" + f" changed to {max_mtu}"
        if 'mtu' in intf:
          log.warning(
            text=strings.eval_format(warning,{'o_name': f"{link._linkname}.{intf.node}"}),
            module="mtu")
          intf.mtu = max_mtu
        if 'mtu' in link:
          log.warning(
            text=strings.eval_format(warning,{'o_name': f"{link._linkname}"}),
            module="mtu")
          link.mtu = max_mtu
