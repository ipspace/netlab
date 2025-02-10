#
# Modified from https://github.com/ssasso/netsim-topologies/blob/main/multivendor-evpn/_plugins/vxlan_anycast_plugin.py
#

import os

from netsim.utils import log
from netsim.augment import addressing, devices, links
from netsim import api, data
from box import Box
import netaddr

_config_name = 'mlag.vtep'
_requires    = [ 'vxlan', 'lag' ]

POOL_NAME = "mlag_vtep"

def pre_link_transform(topology: Box) -> None:
  global _config_name
  # Error if vxlan/lag module is not loaded
  if 'vxlan' not in topology.module or 'lag' not in topology.module:
    log.error(
      'vxlan and/or lag module is not loaded.',
      log.IncorrectValue,
      _config_name)

def topology_expand(topology: Box) -> None:
    # Create address pool to check for overlap with other address ranges
    topology.addressing[POOL_NAME] = { 'ipv4'   : topology.defaults.mlag.vtep.address_pool,
                                       'prefix' : 32 }

def post_transform(topology: Box) -> None:
    # Allocate ANYCAST mlag VTEP Address for the loopbacks
    change_ip = {}
    for link in topology.get('links', []):
      # Only for mlag peer links, XXX assuming at most 1 peergroup per node
      if not link.get('lag.mlag.peergroup', False):
        continue
      peers = link.get('interfaces',[])
      if peers:
        # vtep address - Replace currently allocated VTEP with a new anycast VTEP generated for each mlag pair
        vtep_a = addressing.get(topology.pools, [POOL_NAME, 'loopback'])['ipv4']
        for i in peers:
          node = topology.nodes[i.node]
          features = devices.get_device_features(node,topology.defaults)
          if not features.get('lag.mlag_vtep',None):
            log.error(f'Node {node.name}({node.device}) is not supported by the mlag.vtep plugin',
                      log.IncorrectValue,_config_name)
            continue
          if 'vtep' in node.vxlan and node.get('lag.mlag.vtep',None) is not False:
            node.lag.mlag.vtep = change_ip[ node.vxlan.vtep ] = str(vtep_a.network)

            if 'mlag_vtep_needs_script' in features.lag:
              api.node_config(node,_config_name)     # Remember that we have to do extra configuration

              # On Cumulus, the source interface remains the unicast IP
            else:
              # Add an extra loopback interface with the allocated VTEP IP
              vtep_loopback = data.get_empty_box()
              vtep_loopback.type = 'loopback'
              vtep_loopback.name = f"MLAG VTEP VXLAN interface shared between {' - '.join([i.node for i in peers])}"
              vtep_loopback.ipv4 = node.lag.mlag.vtep + "/32"
              vtep_loopback.vxlan.vtep = True
              links.create_virtual_interface(node, vtep_loopback, topology.defaults)
              if 'ospf' in node.get('module',[]):    # Add it to OSPF when used, TODO ISIS
                vtep_loopback.ospf = { 'area': "0.0.0.0", 'passive': True }
              node.interfaces.append( vtep_loopback )

              # Update VXLAN VTEP
              node.vxlan.vtep_interface = vtep_loopback.ifname
              node.vxlan.vtep = node.lag.mlag.vtep

    for n, ndata in topology.nodes.items():
      # Update remote vtep list in case of static flooding
      if ndata.vxlan.get('flooding', '') == 'static':

        def replace(ip: str) -> str:
           return change_ip[ip] if ip in change_ip else ip
        mlag_vtep = ndata.get('lag.mlag.vtep',None)
        ndata.vxlan.vtep_list = list({ replace(v) for v in ndata.vxlan.vtep_list if replace(v)!=mlag_vtep })
        for vl, vdata in ndata.get('vlans', {}).items():
          if 'vtep_list' in vdata:
            vdata.vtep_list = list({ replace(v) for v in vdata.vtep_list if replace(v)!=mlag_vtep })
