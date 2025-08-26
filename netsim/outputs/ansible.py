#
# Create Ansible inventory
#
import os
import typing

from box import Box

from ..augment import devices, nodes, plugin
from ..data import append_to_list, global_vars
from ..utils import files as _files
from ..utils import log, strings, templates
from ..utils import routing as _rp_utils
from . import _TopologyOutput, check_writeable

forwarded_port_name = { 'ssh': 'ansible_port', }

def copy_provider_inventory(host: Box, p_data: Box) -> None:
  if 'inventory' in p_data:
    for k,v in p_data.inventory.items():
      host[k] = v

  if 'inventory_port_map' in p_data and 'forwarded' in p_data:
    for k,v in p_data.inventory_port_map.items():
      if k in p_data.forwarded:
        host[v] = p_data.forwarded[k] + host.id

def copy_device_provider_group_vars(host: Box, node: Box, topology: Box) -> None:
  p_data = devices.get_provider_data(node,topology.defaults)
  if not 'group_vars' in p_data:
    return

  for k,v in p_data.group_vars.items():
    if not k in host:
      host[k] = v

def provider_inventory_settings(host: Box, node: Box, topology: Box) -> None:
  defaults = topology.defaults
  node_provider = devices.get_provider(node,topology)
  p_data = defaults.providers[node_provider]
  if p_data:
    copy_provider_inventory(host,p_data)

  if 'provider' in node:                                              # Is the node using a secondary provider?
    copy_device_provider_group_vars(host,node,topology)

topo_to_host = { 'mgmt.ipv4': 'ansible_host', 'hostname': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node: Box, topology: Box) -> Box:
  host = Box({})
  for (node_key,inv_key) in topo_to_host.items():
    if "." in node_key:
      value = node[node_key]
    else:
      value = node.get(node_key,None)
    if value:
      host[inv_key] = value

  for (k,v) in node.items():
    if not k in topo_to_host_skip:
      host[k] = v

  provider_inventory_settings(host,node,topology)
  return host

"""
Create a 'hosts' dictionary listing usable IPv4 and IPv6 addresses of all lab devices.
"""
def get_host_addresses(topology: Box) -> Box:
  hosts = global_vars.get('hosts')                          # Try to use a cached version
  if hosts:
    return hosts

  for name,node in topology.nodes.items():
    intf_list = node.interfaces
    if 'loopback' in node:                                  # Create a list of all usable interfaces
      intf_list = [ node.loopback ] + node.interfaces       # ... starting with loopback
      for af in ['ipv4','ipv6']:
        # If the loopback interface has the desired address, extract IP address from the CIDR prefix
        #
        if af in node.loopback and isinstance(node.loopback[af],str):
          lb = _rp_utils.get_intf_address(node.loopback[af])
          append_to_list(hosts[name],'loopback',lb)

    for intf in intf_list:                                  # Now iterate over interfaces
      h_name = f'{name}-{intf.vrf}' if 'vrf' in intf else name
      for af in ('ipv4','ipv6'):                            # ... and collect IPv4 and IPv6 addresses
        if not isinstance(intf.get(af,False),str):          # Is the IP address a string (= usable IP address)?
          continue
      
        addr = _rp_utils.get_intf_address(intf[af])         # Extract IP address from the CIDR prefix
        append_to_list(hosts[h_name],af,addr)               # ... and append it to the list of usable IP addresses

  global_vars.set('hosts',hosts)                            # Cache the hosts dictionary
  return hosts

"""
Add the hosts dictionary to Ansible inventory as an 'all' group variable 
"""
def add_host_addresses(topology: Box, inventory: Box) -> None:
  inventory.all.vars.hosts = get_host_addresses(topology)

"""
Copy defaults.paths dictionary into ALL group. Create separate variables
from individual customizable paths to prevent dependencies on too many
variables that might not be set (example: only 'paths.custom' values should
depend on 'custom_config' variable)
"""
def copy_paths(inventory: Box, topology: Box) -> None:
  if 'paths' not in topology.defaults:
    return
  
  for k,v in topology.defaults.paths.items():
    inventory.all.vars[f'paths_{k}'] = v

"""
Copy other interesting global topology data into all group to make it accessible to all nodes
"""
def copy_global_vars(inventory: Box, topology: Box) -> None:
  for kw in ['prefix']:
    if kw not in topology:
      continue
    inventory.all.vars[kw] = topology[kw]

def create(topology: Box) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  inventory.all.vars.netlab_provider = topology.defaults.provider
  inventory.all.vars.netlab_name = topology.name
  copy_paths(inventory,topology)
  copy_global_vars(inventory,topology)

  inventory.modules.hosts = {}
  inventory.custom_configs.hosts = {}
  inventory.daemons.hosts = {}

  defaults = topology.defaults

  if 'module' in topology:
    inventory.modules.vars.netlab_module = topology.module

  if 'addressing' in topology:
    inventory.all.vars.pools = topology.addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  add_host_addresses(topology,inventory)    # Create the 'hosts' dictionary in 'all' group

  extra_groups: dict = {                    # Extra groups created in Ansible inventory
    'module':  'modules',                   # Devices using configuration modules
    'config':  'custom_configs',            # Devices using custom configuration
    '_daemon': 'daemons'                    # Daemons
  }

  for name,node in topology.nodes.items():
    group = node.get('device','all')
    inventory[group].hosts[name] = ansible_inventory_host(node,topology)

    for xg in extra_groups.keys():
      if node.get(xg,False):                # Add device to the extra group if it has the corresponding attribute set
        inventory[extra_groups[xg]].hosts[name] = {}

  if 'devices' in defaults:
    for group in inventory.keys():
      if group in defaults.devices:
        devdata = defaults.devices[group]
        group_vars = devdata.group_vars + devdata[defaults.provider].group_vars
        # add device features to device group_vars
        group_vars.features = devdata.features
        if group_vars:
          inventory[group]['vars'] = group_vars

  if (inventory.custom_configs.hosts):
    try:
      inventory.custom_configs.vars.netlab_custom_config = plugin.sort_extra_config(topology)
    except log.FatalError as ex:
      log.fatal(f'Cannot sort custom configuration requests: {str(ex)}','ansible',header=True)

  if not 'groups' in topology:
    return inventory

  for gname,gdata in topology.groups.items():
    if not gname in inventory:
      inventory[gname] = { 'hosts': {} }

    if 'vars' in gdata:
      inventory[gname].vars = inventory[gname].get('vars',{}) + gdata.vars

    if 'members' in gdata:
      for m in gdata.members:
        if m in topology.nodes:
          if not m in inventory[gname].hosts:
            inventory[gname].hosts[m] = {}
        elif m in topology.groups:
          inventory[gname].children[m] = {}

  return inventory

# Note to self: the dump function is used by the testing scripts. Do not remove
#
def dump(data: Box) -> None:
  print("Ansible inventory data")
  print("===============================")
  inventory = create(data)
  print(strings.get_yaml_string(inventory))

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  _files.create_file_from_text(fname,header+"\n"+strings.get_yaml_string(data))

min_inventory_data = [ 'id','ansible_host','ansible_port','ansible_connection','ansible_user','ansible_ssh_pass' ]

def ansible_inventory(topology: Box, fname: typing.Optional[str] = 'hosts.yml', hostvars: typing.Optional[str] = 'dirs') -> None:
  inventory = create(topology)

#  import ipdb; ipdb.set_trace()
  header = "# Ansible inventory created from %s\n#\n" % topology.get('input','<unknown>')

  if not fname:
    fname = 'hosts.yml'
  if not hostvars:
    hostvars = "dirs"

  if hostvars == "min":
    write_yaml(inventory,fname,header)
    log.status_created()
    print(f"single-file Ansible inventory {fname}")
    return

  for g in inventory.keys():
    gvars = inventory[g].pop('vars',None)
    if gvars:
      write_yaml(gvars,'group_vars/%s/topology.yml' % g,header)
      if not log.QUIET:
        strings.print_colored_text('[GROUPS]  ','bright_cyan','Created ')
        print(f"group_vars for {g}")

    if 'hosts' in inventory[g]:
      hosts = inventory[g]['hosts']
      for h in hosts.keys():
        if not hosts[h]:
          continue
        min_host = Box({})
        vars_host = Box({})
        for item in hosts[h].keys():
          if item in min_inventory_data:
            min_host[item] = hosts[h][item]
          else:
            vars_host[item] = hosts[h][item]

        write_yaml(vars_host,'host_vars/%s/topology.yml' % h,header)
        if not log.QUIET:
          strings.print_colored_text('[HOSTS]   ','bright_cyan','Created ')
          print(f"host_vars for {h}")
        hosts[h] = min_host

  write_yaml(inventory,fname,header)
  log.status_created()
  print(f"minimized Ansible inventory {fname}")

def ansible_config(config_file: typing.Union[str,None] = 'ansible.cfg', inventory_file: typing.Union[str,None] = 'hosts.yml') -> None:
  if not config_file:
    config_file = 'ansible.cfg'
  if not inventory_file:
    inventory_file = 'hosts.yml'

  try:
    cfg_text = templates.render_template(
                j2_file='ansible.cfg.j2',
                data={'inventory': inventory_file or 'hosts.yml'},
                path='templates',
                extra_path=_files.get_search_path('ansible'))
  except Exception as ex:
    log.fatal(
      text=f"Error rendering ansible.cfg\n{strings.extra_data_printout(str(ex))}",
      module='ansible')

  _files.create_file_from_text(config_file,cfg_text)
  if not log.QUIET:
    log.status_created()
    print(f"Ansible configuration file: {config_file}")

class AnsibleInventory(_TopologyOutput):

  DESCRIPTION :str = 'Ansible inventory and configuration file'

  def write(self, topology: Box) -> None:
    check_writeable('Ansible inventory')
    hostfile = self.settings.hostfile or 'hosts.yml'
    configfile = self.settings.configfile or 'ansible.cfg'
    output_format = None

    if hasattr(self,'filenames'):
      hostfile = self.filenames[0]
      if len(self.filenames) > 1:
        configfile = self.filenames[1]
      if len(self.filenames) > 2:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[2:]),log.IncorrectValue,'ansible')

    if self.format:
      output_format = self.format[0]
    
    # Creates a "ghost clean" topology
    # (AKA, remove unmanaged devices)
    ansible_topology = nodes.ghost_buster(topology)

    ansible_inventory(ansible_topology,hostfile,output_format)
    ansible_config(configfile,hostfile)
