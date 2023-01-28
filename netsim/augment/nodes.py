'''
Create detailed node-level data structures from topology

* Discover desired imagex (boxes)
* Add default module list to nodes without specific modules
* Set loopback and management interface data
'''
import typing

from box import Box

from .. import common
from .. import utils
from .. import addressing
from .. import providers
from . import devices
from ..data.validate import validate_attributes,must_be_int,must_be_string
from ..modules._dataplane import extend_id_set,is_id_used,set_id_counter,get_next_id

"""
Reserve a node ID, for example for gateway ID, return True if successful, False if duplicate
"""
def reserve_id(n_id: int) -> bool:
  if is_id_used('node_id',n_id):
    return False

  extend_id_set('node_id',set([n_id]))
  return True

"""
Node data structure is a dictionary. Convert lists of dictionaries (now obsolete)
Or lists of strings into a unified dictionary structure
"""

def create_node_dict(nodes: Box) -> Box:
  if isinstance(nodes,dict):
    node_dict = nodes
  else:
    node_dict = Box({},default_box=True,box_dots=True)
    for n in nodes or []:
      if isinstance(n,dict):
        if not 'name' in n:
          common.error(f'Node is missing a "name" attribute: {n}',common.IncorrectValue,'nodes')
          continue
      elif isinstance(n,str):
        n = Box({ 'name': n },default_box=True,box_dots=True)
      node_dict[n.name] = n

  for name in list(node_dict.keys()):
    ndata = node_dict[name]
    if ndata is None:
      ndata = Box({'name': name},default_box=True)
    elif not isinstance(ndata,dict):
      common.error(f'Node data for node {name} must be a dictionary')
      node_dict[name] = { 'name': name, 'extra': ndata }
      ndata = node_dict[name]
    else:
      ndata['name'] = name

    ndata.interfaces = ndata.interfaces or []   # Make sure node.interfaces is always defined
    node_dict[name] = ndata

  common.exit_on_error()
  return node_dict

"""
Validate node attributes
"""
def validate(topology: Box) -> None:
  for n_name,n_data in topology.nodes.items():
    providers = list(topology.defaults.providers.keys())
    validate_attributes(
      data=n_data,                                    # Validate node data
      topology=topology,
      data_path=f'nodes.{n_name}',                    # Topology path to node name
      data_name=f'node',
      attr_list=['node'],                             # We're checking node attributes
      modules=n_data.get('module',[]),                # ... against node modules
      module='nodes',                                 # Function is called from 'nodes' module
      extra_attributes = providers)                   # Allow provider-specific settings (not checked at the moment)

def augment_mgmt_if(node: Box, defaults: Box, addrs: typing.Optional[Box]) -> None:
  if 'ifname' not in node.mgmt:
    mgmt_if = devices.get_device_attribute(node,'mgmt_if',defaults)
    if not mgmt_if:
      ifname_format = devices.get_device_attribute(node,'interface_name',defaults)
      if not isinstance(ifname_format,str):
        common.fatal("Missing interface name template for device type %s" % node.device)
        return

      ifindex_offset = devices.get_device_attribute(node,'ifindex_offset',defaults)
      if ifindex_offset is None:
        ifindex_offset = 1

      mgmt_if = utils.strings.eval_format(ifname_format,{'ifindex': ifindex_offset - 1 })

    node.mgmt.ifname = mgmt_if

  # If the mgmt ipaddress is statically set (IPv4/IPv6)
  # skip the address set
  if 'ipv4' in node.mgmt or 'ipv6' in node.mgmt:
    return

  if not addrs:                                                       # We need a management address pool, but there's none
    common.error(
      f"Node {node.name} does not have a management IP address and there's no 'mgmt' address pool",
      common.MissingValue,
      'nodes')
    return

  for af in 'ipv4','ipv6':                                            # Try to assign IPv4 or IPv6 management address
    pfx = af + '_pfx'
    if not pfx in addrs:                                              # ... desired AF not in management pool, try the next one
      continue

    if not addrs.get('start'):
      common.fatal("Start offset missing in management address pool for AF %s" % af)

    try:                                                              # Try to assign management address (might fail due to large ID)
      node.mgmt[af] = str(addrs[pfx][node.id+addrs.start])
    except Exception as ex:
      common.error(
        f'Cannot assign management address from prefix {str(addrs[pfx])} (starting at {addrs.start}) to node with ID {node.id}',
        common.IncorrectValue,
        'nodes')

  if addrs.mac_eui and not 'mac' in node.mgmt:                        # Finally, assign management MAC address
    addrs.mac_eui[5] = node.id
    node.mgmt.mac = str(addrs.mac_eui)

  if not 'ipv4' in node.mgmt and not 'ipv6' in node.mgmt:             # Final check: did we get a usable management address?
    common.error(
      f'Node {node.name} does not have a usable management IP addresss',
      common.MissingValue,
      'nodes')

"""
Add device data to nodes
"""

def find_node_device(n: Box, topology: Box) -> bool:
  if 'device' not in n:
    n.device = topology.defaults.device

  if not n.device:
    common.error(
      f'No device type specified for node {n.name} and there is no default device type',
      common.MissingValue,
      'nodes')
    return False

  try:
    must_be_string(n,'device',f'nodes.{n.name}',module='nodes',abort=True)
  except Exception as ex:
    return False

  devtype = n.device

  if not devtype in topology.defaults.devices:
    common.error(f'Unknown device {devtype} in node {n.name}',common.IncorrectValue,'nodes')
    return False

  dev_def = topology.defaults.devices[devtype]
  if not isinstance(dev_def,dict):
    common.fatal(f"Device data for device {devtype} must be a dictionary")

  for kw in ['interface_name','description']:
    if not kw in dev_def:
      common.error(
        f'Device {devtype} used on node {n.name} is not a valid device type\n'+
        "... run 'netlab show devices' to display valid device types",
        common.IncorrectValue,
        'nodes')
      return False

  return True

"""
Find the image/box for the container/device
"""
def find_node_image(n: Box, topology: Box) -> bool:
  provider = devices.get_provider(n,topology.defaults)

  pdata = devices.get_provider_data(n,topology.defaults)
  if 'node' in pdata:
    if not isinstance(pdata.node,Box):    # pragma: no cover
      common.fatal(f"Node data for device {n.device} provider {provider} must be a dictionary")
      return False
    n[provider] = pdata.node + n.get(provider,{})

  if n.box:
    return True

  if 'image' in n:
    n.box = n.image
    del n['image']
    return True

  if 'image' in topology.defaults.devices[n.device]:
    if not must_be_string(topology.defaults.devices[n.device],'image',f'defaults.devices.{n.device}',module='nodes'):
      return False

    n.box = topology.defaults.devices[n.device].image
    return True

  if 'image' in pdata:
    if not must_be_string(pdata,'image',f'defaults.devices.{n.device}.{provider}.image',module='nodes'):
      return False

    n.box = pdata.image
    return True

  common.error(
    f'No image specified for device {n.device} (provider {provider}) used by node {n.name}',
    common.MissingValue,
    'nodes')

  return False

"""
Validate provider setting used in a node
"""

def validate_node_provider(n: Box, topology: Box) -> bool:
  if not 'provider' in n:
    return True

  if not n.provider in topology.defaults.providers:
    common.error(
      f'Invalid provider {n.provider} specified in node {n.name}',
      common.IncorrectValue,
      'nodes')
    return False

  if not n.provider in topology.defaults.providers[topology.provider]:
    common.error(
      f'Provider {n.provider} specified in node {n.name} is not compatible with lab topology provider {topology.provider}',
      common.IncorrectValue,
      'nodes')
    return False

  topology[topology.provider].providers[n.provider] = True
  return True

"""
Add provider data to nodes:

* Check whether the node device exists
* Copy device.provider.node into node.provider
* Get device image
"""
def augment_node_provider_data(topology: Box) -> None:
  if not topology.defaults.devices:
    common.fatal('Device defaults (defaults.devices) are missing')

  for name,n in topology.nodes.items():
    if not validate_node_provider(n,topology):
      continue

    if not find_node_device(n,topology):
      continue

    if not find_node_image(n,topology):
      continue

"""
Add system data to devices -- hacks that are not yet covered in the settings structure
"""
def augment_node_system_data(topology: Box) -> None:
  if 'mtu' in topology.defaults.get('interfaces',{}):
    if not isinstance(topology.defaults.interfaces.mtu,int):            # pragma: no cover
      common.error(
        'defaults.interfaces.mtu setting should be an integer',
        common.IncorrectValue,
        'topology')
    else:
      for n in topology.nodes.values():
        if not 'mtu' in n:
          n.mtu = topology.defaults.interfaces.mtu
        else:
          if not isinstance(n.mtu,int):                                 # pragma: no cover
            common.error(
              f'nodes.{n.name}.mtu setting should be an integer',
              common.IncorrectValue,
              'nodes')

"""
augment_node_device_data: copy attributes that happen to be node attributes from device defaults into node data
"""

def augment_node_device_data(n: Box, defaults: Box) -> None:
  node_attr = defaults.attributes.get('node',[])
  dev_data  = devices.get_consolidated_device_data(n,defaults)

  for attr in node_attr:                      # Copy known node attributes from device+provider data into node data
    if attr in dev_data and not attr in n:
      n[attr] = dev_data[attr]

  if 'node' in defaults.devices[n.device]:    # Copy everything within device (but not provider) node dictionary into node data
    for k in defaults.devices[n.device].node.keys():
      if not k in n:
        n[k] = defaults.devices[n.device].node[k]

'''
Main node transformation code

* set node ID
* set loopback address(es)
* copy device data from defaults
* set management IP and MAC addresses
'''
def transform(topology: Box, defaults: Box, pools: Box) -> None:
  for name,n in topology.nodes.items():
    if not must_be_int(n,'id',f'nodes.{name}',module='nodes',min_value=1,max_value=250):
      continue
    if not reserve_id(n.id):
      common.error(
        f'Duplicate static node ID {n.id} on node {n.name}',
        common.IncorrectValue,
        'nodes')

  common.exit_on_error()
  set_id_counter('node_id',1,250)
  for name,n in topology.nodes.items():
    if not 'id' in n:
      n.id = get_next_id('node_id')

    if not n.name: # pragma: no cover (name should have been checked way before)
      common.fatal(f"Internal error: node does not have a name {n}",'nodes')
      return

    augment_node_device_data(n,defaults)

    if pools.loopback and n.get('role','') != 'host':
      prefix_list = addressing.get(pools,['loopback'],n.id)
      for af in prefix_list:
        if isinstance(prefix_list[af],bool):
          if prefix_list[af]:
            common.fatal( f"Loopback addresses must be valid IP prefixes, not 'True': {prefix_list}" )
        elif not n.loopback[af]:
          if af == 'ipv6':
            n.loopback[af] = addressing.get_addr_mask(prefix_list[af],1)
          else:
            n.loopback[af] = str(prefix_list[af])

    augment_mgmt_if(n,defaults,topology.addressing.mgmt)
    providers.execute_node("augment_node_data",n,topology)

'''
Return a copy of the topology (leaving original topology unchanged) with unmanaged devices removed
'''
def ghost_buster(topology: Box) -> Box:
  common.print_verbose('Removing unmanaged devices from topology')
  # Create a copy of topology
  topo_copy = Box(topology,default_box=True,box_dots=True)
  
  # Remove all nodes with "unmanaged" flag set
  topo_copy.nodes = { k:v for k,v in topo_copy.nodes.items() if not v.get('unmanaged',False) }  
  return topo_copy
