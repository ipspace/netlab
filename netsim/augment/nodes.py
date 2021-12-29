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

#
# Starting with release 1.1, the nodes data structure is a dictionary. Convert
# lists of dictionaries or lists of strings into a unified dictionary structure
#
def create_node_dict(nodes: Box) -> Box:
  if isinstance(nodes,dict):
    node_dict = nodes
  else:
    node_dict = Box({},default_box=True,box_dots=True)
    node_id = 0
    for n in nodes or []:
      if isinstance(n,dict):
        if not 'name' in n:
          common.error(f'Node is missing a "name" attribute: {n}',common.IncorrectValue,'nodes')
          continue
      elif isinstance(n,str):
        n = Box({ 'name': n },default_box=True,box_dots=True)
      node_id = node_id + 1
      n.id = node_id
      node_dict[n.name] = n

  for name in list(node_dict.keys()):
    ndata = node_dict[name]
    if ndata is None:
      ndata = Box({'name': name},default_box=True)
    elif not isinstance(ndata,dict):
      common.error(f'Node data for node {name} must be a dictionary')
      node_dict[name] = { 'name': name, 'extra': ndata }
    else:
      ndata['name'] = name
    node_dict[name] = ndata

  common.exit_on_error()
  return node_dict

def augment_mgmt_if(node: Box, device_data: Box, addrs: typing.Optional[Box]) -> None:
  if 'ifname' not in node.mgmt:
    mgmt_if = device_data.mgmt_if
    if not mgmt_if:
      ifname_format = device_data.interface_name
      if not ifname_format:
        common.fatal("Missing interface name template for device type %s" % node.device)

      ifindex_offset = device_data.get('ifindex_offset',1)
      mgmt_if = ifname_format % (ifindex_offset - 1)
    node.mgmt.ifname = mgmt_if

  if addrs:
    for af in 'ipv4','ipv6':
      pfx = af + '_pfx'
      if pfx in addrs:
        if not addrs.get('start'):
          common.fatal("Start offset missing in management address pool for AF %s" % af)
        if not af in node.mgmt:
          node.mgmt[af] = str(addrs[pfx][node.id+addrs.start])

    if addrs.mac_eui and not 'mac' in node.mgmt:
      addrs.mac_eui[5] = node.id
      node.mgmt.mac = str(addrs.mac_eui)

#
# Add device (box) images from defaults
#
def augment_node_provider_data(topology: Box) -> None:
  provider = topology.provider
  devices = topology.defaults.devices
  if not devices:
    common.fatal('Device defaults (defaults.devices) are missing')

  for name,n in topology.nodes.items():
    if not n.device:
      n.device = topology.defaults.device

    if not n.device:
      common.error(
        f'No device type specified for node {name} and there is no default device type',
        common.MissingValue,
        'nodes')
      continue

    devtype = n.device

    if not devtype in devices:
      common.error(f'Unknown device {devtype} in node {name}',common.IncorrectValue,'nodes')
      continue

    if not isinstance(devices[devtype],dict):
      common.fatal(f"Device data for device {devtype} must be a dictionary")

    for k,v in devices[devtype].items():
      if "provider_" in k:
        p_key = k.replace("provider_","")
        if not p_key in n:
          n[p_key] = v

    if n.box:
      continue
    if 'image' in n:
      n.box = n.image
      del n['image']
      continue

    if not 'image' in devices[devtype]:
      common.error(f"No image data for device type {devtype} used by node {name}",common.MissingValue,'nodes')
      continue

    if not isinstance(devices[devtype].image,dict):
      common.error(
        f"Image data for device type {devtype} used by node {name} should be a dictionary",
        common.IncorrectValue,
        'nodes')
      continue

    box = devices[devtype].image[provider]
    if not box:
      common.error(
        f'No image specified for device {devtype} (provider {provider}) used by node {name}',
        common.MissingValue,
        'nodes')
      continue

    n.box = box

'''
get_next_id: given a list of static IDs and the last ID, get the next device ID
'''
def get_next_id(id_list: list, id: int) -> int:
  while id < 254:
    id = id + 1
    if not id in id_list:
      return id

  common.fatal(
    'Cannot get the next device ID. The lab topology is probably too big')  # pragma: no cover (I'm not going to write a test case for this one)
  return -1                                                                 # pragma: no cover (making mypy happy)

'''
Main node transformation code

* set node ID
* set loopback address(es)
* copy device data from defaults
* set management IP and MAC addresses
'''
def transform(topology: Box, defaults: Box, pools: Box) -> None:
  id = 0
  id_list = []

  for name,n in topology.nodes.items():
    if 'id' in n:
      if isinstance(n.id,int) and n.id > 0 and n.id <= 250:
        id_list.append(n.id)
      else:
        common.error('Device ID must be an integer between 1 and 250')

  common.exit_on_error()

  for name,n in topology.nodes.items():
    if not 'id' in n:
      id = get_next_id(id_list,id)
      n.id = id

    if not n.name: # pragma: no cover (name should have been checked way before)
      common.fatal(f"Internal error: node does not have a name {n}",'nodes')
      return

    if pools.loopback:
      prefix_list = addressing.get(pools,['loopback'],n.id)
      for af in prefix_list:
        if af == 'ipv6':
          n.loopback[af] = addressing.get_addr_mask(prefix_list[af],1)
        else:
          n.loopback[af] = str(prefix_list[af])

    device_data = defaults.devices[n.device]
    if not device_data: # pragma: no cover (should never get this far -- this should have been caught earlier on)
      common.fatal(f"Missing device data for device type {n.device} used by node {name}",'nodes')
      continue

    augment_mgmt_if(n,device_data,topology.addressing.mgmt)

    topology.Provider.call("augment_node_data",n,topology)
