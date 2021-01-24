#
# Build full-blown topology data model from high-level topology
#

import netaddr
import common
import addressing
import os

def adjust_node_list(nodes):
  node_list = []
  if isinstance(nodes, dict):
    for k,v in sorted(nodes.items()):
      if v is None:
        v = {}
      elif not isinstance(v,dict):
        common.error('Node data for node %s must be a dictionary' % k)
        v = { 'extra': v }
      v['name'] = k
      node_list.append(v)
  else:
    for n in nodes:
      node_list.append(n if type(n) is dict else { 'name': n })
  return node_list

def augment_mgmt_if(node,device_data,addrs):
  if 'mgmt' not in node:
    node['mgmt'] = {}

  if 'ifname' not in node['mgmt']:
    mgmt_if = device_data.get('mgmt_if')
    if not mgmt_if:
      ifname_format = device_data.get('interface_name')
      if not ifname_format:
        common.fatal("Missing interface name template for device type %s" % n['device'])

      ifindex_offset = device_data.get('ifindex_offset',1)
      mgmt_if = ifname_format % (ifindex_offset - 1)
    node['mgmt']['ifname'] = mgmt_if

  if addrs:
    for af in 'ipv4','ipv6':
      pfx = af + '_pfx'
      if pfx in addrs:
        if not af in node['mgmt']:
          node['mgmt'][af] = str(addrs[pfx][node['id']+addrs['start']])

    if 'mac_eui' in addrs:
      addrs['mac_eui'][5] = node['id']
      if not 'mac' in node['mgmt']:
        node['mgmt']['mac'] = str(addrs['mac_eui'])

def augment_node_images(topology):
  provider = topology['provider']
  devices = common.get_value(topology,['defaults','devices'])
  if not devices:
    common.fatal('Device defaults (defaults.devices) are missing')

  for n in topology['nodes']:
    if 'box' in n:
      continue
    if 'image' in n:
      n['box'] = n['image']
      del n['image']
      continue

    devtype = n['device']
    if not devtype in devices:
      common.error('Unknown device %s in node %s' % (devtype,n['name']))
      continue

    box = common.get_value(data=devices,path=[devtype,'image',provider])
    if not box:
      common.error('No image specified for device %s (provider %s) used by node %s' % (devtype,provider,n['name']))
      continue

    n['box'] = box

def transform(topology,defaults,pools):
  augment_node_images(topology)

  id = 0
  ndict = {}
  for n in topology['nodes']:
    id = id + 1
    if 'id' in n:
      common.error("ERROR: static node IDs are not supported, overwriting with %d: %s" % (id,str(n)))
    n['id'] = id

    if not n.get('name'):
      common.error("ERROR: node does not have a name %s" % str(n))
      continue

    if 'loopback' in pools:
      n['loopback'] = {}
      prefix_list = addressing.get(pools,['loopback'])
      for af in prefix_list:
        if af == 'ipv6':
          n['loopback'][af] = addressing.get_addr_mask(prefix_list[af],1)
        else:
          n['loopback'][af] = str(prefix_list[af])

    if not 'device' in n:
      n['device'] = defaults.get('device')

    device_data = common.get_value( \
                data=defaults,
                path=['devices',n['device']])
    if not device_data:
      common.error("ERROR: Unsupported device type %s: %s" % (n['device'],n))
      continue

    augment_mgmt_if(n,device_data,topology['addressing'].get('mgmt'))

    if 'box' in device_data:
      n['box'] = device_data['box']

    ndict[n['name']] = n

  topology['nodes_map'] = ndict
  return ndict
