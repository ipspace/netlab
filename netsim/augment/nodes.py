'''
Create detailed node-level data structures from topology

* Discover desired imagex (boxes)
* Add default module list to nodes without specific modules
* Set loopback and management interface data
'''
import typing

from box import Box
import netaddr

from ..utils import log
from .. import data
from .. import utils
from .. import providers
from . import devices,addressing
from ..data.validate import validate_attributes,get_object_attributes
from ..data.types import must_be_int,must_be_string,must_be_id,must_be_device
from ..data import global_vars
from ..modules._dataplane import extend_id_set,is_id_used,set_id_counter,get_next_id

MAX_NODE_ID: typing.Final[int] = 250

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
    node_dict = data.get_empty_box()
    for n in nodes or []:
      if isinstance(n,dict):
        if not 'name' in n:
          log.error(f'Node is missing a "name" attribute: {n}',log.IncorrectValue,'nodes')
          continue
      elif isinstance(n,str):
        n = data.get_box({ 'name': n })
      node_dict[n.name] = n

  for name in list(node_dict.keys()):
    ndata = node_dict[name]
    if ndata is None:
      ndata = data.get_box({'name': name})
    elif not isinstance(ndata,dict):
      log.error(
        text=f'Node data for node {name} must be a dictionary',
        category=log.IncorrectType,
        module='nodes')
      node_dict[name] = { 'name': name, 'extra': ndata }
      ndata = node_dict[name]
    else:
      ndata['name'] = name

    ndata.interfaces = ndata.interfaces or []   # Make sure node.interfaces is always defined
    node_dict[name] = ndata

  log.exit_on_error()
  return node_dict

"""
Validate node attributes
"""
def validate(topology: Box) -> None:
  # Allow provider- and tool- specific node attributes
  extra = get_object_attributes(['providers','tools'],topology)
  for n_name,n_data in topology.nodes.items():
    must_be_id(
      parent=None,
      key=n_name,
      path=f'NOATTR:node name {n_name}',
      max_length=global_vars.get_const('MAX_NODE_ID_LENGTH',16),
      module='nodes')
    validate_attributes(
      data=n_data,                                    # Validate node data
      topology=topology,
      data_path=f'nodes.{n_name}',                    # Topology path to node name
      data_name=f'node',
      attr_list=['node'],                             # We're checking node attributes
      modules=n_data.get('module',[]),                # ... against node modules
      module='nodes',                                 # Function is called from 'nodes' module
      ignored=['_','netlab_','ansible_'],             # Ignore attributes starting with _, netlab_ or ansible_
      extra_attributes=extra)                         # Allow provider- and tool-specific settings

def augment_mgmt_if(node: Box, defaults: Box, addrs: typing.Optional[Box]) -> None:
  if 'ifname' not in node.mgmt:
    mgmt_if = devices.get_device_attribute(node,'mgmt_if',defaults)
    if not mgmt_if:
      ifname_format = devices.get_device_attribute(node,'interface_name',defaults)
      if not isinstance(ifname_format,str):
        log.fatal("Missing interface name template for device type %s" % node.device)
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
    log.error(
      f"Node {node.name} does not have a management IP address and there's no 'mgmt' address pool",
      log.MissingValue,
      'nodes')
    return

  for af in 'ipv4','ipv6':                                            # Try to assign IPv4 or IPv6 management address
    pfx = af + '_pfx'
    if not pfx in addrs:                                              # ... desired AF not in management pool, try the next one
      continue

    if not addrs.get('start'):
      log.fatal(
        "Start offset missing in management address pool for AF %s" % af,
        module='addressing',
        header=True)

    try:                                                              # Try to assign management address (might fail due to large ID)
      node.mgmt[af] = str(addrs[pfx][node.id+addrs.start])
    except Exception as ex:
      log.error(
        f'Cannot assign management address from prefix {str(addrs[pfx])} (starting at {addrs.start}) to node with ID {node.id}',
        log.IncorrectValue,
        'nodes')

  if addrs.mac_eui and not 'mac' in node.mgmt:                        # Finally, assign management MAC address
    addrs.mac_eui[5] = node.id
    node.mgmt.mac = addrs.mac_eui.format(netaddr.mac_unix_expanded)

  if not 'ipv4' in node.mgmt and not 'ipv6' in node.mgmt:             # Final check: did we get a usable management address?
    log.error(
      f'Node {node.name} does not have a usable management IP addresss',
      log.MissingValue,
      'nodes')

"""
Add device data to nodes
"""

def find_node_device(n: Box, topology: Box) -> bool:
  if 'device' not in n:
    n.device = topology.defaults.device

  if not n.device:
    log.error(
      f'No device type specified for node {n.name} and there is no default device type',
      log.MissingValue,
      'nodes')
    return False

  try:
    must_be_device(n,'device',f'nodes.{n.name}',module='nodes',_abort=True)
  except Exception as ex:
    return False

  devtype = n.device

  dev_def = topology.defaults.devices[devtype]
  if not isinstance(dev_def,Box):
    log.fatal(f"Device data for device {devtype} must be a dictionary")

  if dev_def.get('node.module') and 'module' not in n:      # Have to copy default device module into node data
    n.module = dev_def.node.module                          # ... before modules are initialized

  return True

"""
Find the image/box for the container/device
"""
def find_node_image(n: Box, topology: Box) -> bool:
  provider = devices.get_provider(n,topology.defaults)

  pdata = devices.get_provider_data(n,topology.defaults)
  if 'node' in pdata:
    if not isinstance(pdata.node,Box):    # pragma: no cover
      log.fatal(f"Node data for device {n.device} provider {provider} must be a dictionary")
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

  log.error(
    f'No image specified for device {n.device} (provider {provider}) used by node {n.name}',
    log.MissingValue,
    'nodes')

  return False

"""
Validate provider setting used in a node
"""

def validate_node_provider(n: Box, topology: Box) -> bool:
  if not 'provider' in n:
    return True

  if n.provider == topology.get('provider',None):
    n.pop('provider',None)
    return True

  if not n.provider in topology.defaults.providers:
    log.error(
      f'Invalid provider {n.provider} specified in node {n.name}',
      log.IncorrectValue,
      'nodes')
    return False

  if not n.provider in topology.defaults.providers[topology.provider]:
    log.error(
      f'Provider {n.provider} specified in node {n.name} is not compatible with lab topology provider {topology.provider}',
      log.IncorrectValue,
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
    log.fatal('Device defaults (defaults.devices) are missing')

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
      log.error(
        'defaults.interfaces.mtu setting should be an integer',
        log.IncorrectValue,
        'topology')
    else:
      for n in topology.nodes.values():
        if not 'mtu' in n:
          n.mtu = topology.defaults.interfaces.mtu
        else:
          if not isinstance(n.mtu,int):                                 # pragma: no cover
            log.error(
              f'nodes.{n.name}.mtu setting should be an integer',
              log.IncorrectValue,
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

  if dev_data.get('daemon',False):                # Special handling of daemons
    n._daemon = True                              # First, set the daemon flag so we don't have to look up the device data
    n._daemon_parent = dev_data.daemon_parent     # Next, remember the parent device -- we need that in template search paths
    if 'daemon_config' in dev_data:               # Does the daemon need special configuration files?
      n._daemon_config = dev_data.daemon_config   # Yes, save it for later (clab binds or Ansible playbooks)

  # Do a sanity check on _daemon_config dictionary. Remove faulty value to prevent downstream crashes
  #
  if '_daemon_config' in n and not isinstance(n._daemon_config,Box):
    log.error(f"Daemon configuration files for node {n} must be a dictionary")
    n.pop('_daemon_config',None)

'''
Main node transformation code

* set node ID
* set loopback address(es)
* copy device data from defaults
* set management IP and MAC addresses
'''
def transform(topology: Box, defaults: Box, pools: Box) -> None:
  for name,n in topology.nodes.items():
    if not must_be_int(n,'id',f'nodes.{name}',module='nodes',min_value=1,max_value=MAX_NODE_ID):
      continue
    if not reserve_id(n.id):
      log.error(
        f'Duplicate static node ID {n.id} on node {n.name}',
        log.IncorrectValue,
        'nodes')

  log.exit_on_error()
  set_id_counter('node_id',1,MAX_NODE_ID)
  for name,n in topology.nodes.items():
    if not 'id' in n:
      n.id = get_next_id('node_id')

    if not n.name: # pragma: no cover (name should have been checked way before)
      log.fatal(f"Internal error: node does not have a name {n}",'nodes')
      return

    augment_node_device_data(n,defaults)

    n.af = {}                                                 # Nodes must have AF attribute
    if pools.loopback and n.get('role','') != 'host':
      prefix_list = addressing.get(pools,['loopback'],n.id)
      for af in prefix_list:
        if isinstance(prefix_list[af],bool):
          if prefix_list[af]:
            log.fatal(
              f"Loopback addresses must be valid IP prefixes, not 'True': {prefix_list}",
              module='topology',
              header=True)
        elif not n.loopback[af]:
          if af == 'ipv6':
            if prefix_list[af].prefixlen == 128:
              n.loopback[af] = str(prefix_list[af])
            else:
              n.loopback[af] = addressing.get_addr_mask(prefix_list[af],1)
          else:
            n.loopback[af] = str(prefix_list[af])
          n.af[af] = True

    if n.get('role','') != 'host':
      lbname = devices.get_loopback_name(n,topology)
      if lbname:
        n.loopback.ifname = lbname
        n.loopback.ifindex = 0
        n.loopback.type = 'loopback'
        n.loopback.neighbors = []

    augment_mgmt_if(n,defaults,topology.addressing.mgmt)
    providers.execute_node("augment_node_data",n,topology)

'''
Final cleanup of node data
'''
def cleanup_daemon_config(n: Box) -> None:
  for k in list(n._daemon_config.keys()):
    if k.startswith('_'):                                   # Skip internal mappings (will have to be redone later)
      continue

    kn = k.replace('@','.')                                 # A workaround for aggressive de-dotting
    # Leave config mappings for device configuration, module configuration, or extra configs
    if kn == n.device or kn in n.get('module',[]) or kn in n.get('config',[]):
      continue

    n._daemon_config.pop(k,None)

def cleanup(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if '_daemon_config' in n:
      cleanup_daemon_config(n)

'''
Return a copy of the topology (leaving original topology unchanged) with unmanaged devices removed
'''
def ghost_buster(topology: Box) -> Box:
  log.print_verbose('Removing unmanaged devices from topology')
  # Create a copy of topology
  topo_copy = data.get_box(topology)
  
  # Remove all nodes with "unmanaged" flag set
  topo_copy.nodes = { k:v for k,v in topo_copy.nodes.items() if not v.get('unmanaged',False) }  
  return topo_copy
