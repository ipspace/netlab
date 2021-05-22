'''
Create detailed node-level data structures from topology

* Discover desired imagex (boxes)
* Add default module list to nodes without specific modules
* Set loopback and management interface data
'''
import typing

from box import Box

from .. import common
from .. import addressing

def adjust_node_list(nodes: typing.Union[typing.Dict, typing.List]) -> typing.List[Box]:
  node_list = []
  if isinstance(nodes, dict):
    for k,v in sorted(nodes.items()):
      if v is None:
        v = Box({},default_box=True)
      elif not isinstance(v,dict):
        common.error('Node data for node %s must be a dictionary' % k)
        v = Box({ 'extra': v })
      v.name = k
      node_list.append(v)
  else:
    for n in nodes:
      if isinstance(n,dict):
        if not 'name' in n:
          common.error('Node is missing a "name" attribute: %s' % n)
      node_list.append(n if isinstance(n,dict) else { 'name': n })
  return node_list

def augment_mgmt_if(node: Box, device_data: Box, addrs: typing.Optional[Box]) -> None:
  node.setdefault('mgmt',{})

  if 'ifname' not in node.mgmt:
    mgmt_if = device_data.mgmt_if
    if not mgmt_if:
      ifname_format = device_data.interface_name
      if not ifname_format:
        common.fatal("Missing interface name template for device type %s" % node['device'])

      ifindex_offset = device_data.get('ifindex_offset',1)
      mgmt_if = ifname_format % (ifindex_offset - 1)
    node.mgmt.ifname = mgmt_if

  if addrs:
    for af in 'ipv4','ipv6':
      pfx = af + '_pfx'
      if pfx in addrs:
        if not af in node.mgmt:
          node.mgmt[af] = str(addrs[pfx][node['id']+addrs['start']])

    if addrs.mac_eui:
      addrs.mac_eui[5] = node['id']
      node.mgmt.setdefault('mac',str(addrs['mac_eui']))

#
# Add device (box) images from defaults
#
def augment_node_provider_data(topology: Box) -> None:
  provider = topology.provider
  devices = topology.defaults.devices
  if not devices:
    common.fatal('Device defaults (defaults.devices) are missing')

  for n in topology.nodes:
    n.setdefault('device',topology.defaults.get('device'))
    if not n.device:
      common.error('No device type specified for node %s and there is no default device type' % n.name)
      continue

    for k,v in topology.defaults.devices[n.device].items():
      if "provider_" in k:
        n[k.replace("provider_","")] = v

    if n.box:
      continue
    if 'image' in n:
      n.box = n.image
      del n['image']
      continue

    devtype = n.device
    if not devtype in devices:
      common.error('Unknown device %s in node %s' % (devtype,n.name))
      continue

    box = devices[devtype].image[provider]
    if not box:
      common.error('No image specified for device %s (provider %s) used by node %s' % (devtype,provider,n['name']))
      continue

    n.box = box

# Rebuild nodes-by-name dict
#
def rebuild_nodes_map(topology: Box) -> None:
  topology.nodes_map = { n.name : n for n in topology.get('nodes',[]) }

'''
Main node transformation code

* set node ID
* set loopback address(es)
* copy device data from defaults
* set management IP and MAC addresses
'''
def transform(topology: Box, defaults: Box, pools: Box) -> typing.Dict:
  augment_node_provider_data(topology)

  id = 0
  ndict = {}
  for n in topology['nodes']:
    id = id + 1
    if n.id:
      common.error("ERROR: static node IDs are not supported, overwriting with %d: %s" % (id,str(n)))
    n.id = id

    if not n.name:
      common.error("ERROR: node does not have a name %s" % str(n))
      continue

    if pools.loopback:
      prefix_list = addressing.get(pools,['loopback'])
      for af in prefix_list:
        if af == 'ipv6':
          n.loopback[af] = addressing.get_addr_mask(prefix_list[af],1)
        else:
          n.loopback[af] = str(prefix_list[af])

    device_data = defaults.devices[n.device]
    if not device_data:
      common.error("ERROR: Unsupported device type %s: %s" % (n.device,n))
      continue

    augment_mgmt_if(n,device_data,topology.addressing.mgmt)

    ndict[n.name] = n
    topology.Provider.call("augment_node_data",n,topology)

  topology.nodes_map = ndict
  return ndict
