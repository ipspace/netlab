#
# Create Ansible inventory
#
import os
import typing

from box import Box

from ..augment import nodes, plugin
from ..utils import files as _files
from ..utils import log, strings, templates
from . import _TopologyOutput, check_writeable
from .common import adjust_inventory_host, get_host_addresses

forwarded_port_name = { 'ssh': 'ansible_port', }


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

  # Create placeholders for well-known groups
  #
  for grp in ('modules','custom_configs','daemons','unprovisioned','netlab_no_reload'):
    inventory[grp].hosts = {}

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
    inventory[group].hosts[name] = adjust_inventory_host(node,defaults=topology.defaults,group_vars=False)

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
    for group in list(inventory.keys()):          # Ansible is unhappy with hyphens in group names
      if '-' in group:                            # So we have to recreate those group entries
        g_correct = group.replace('-','_')        # ... replacing hyphens with underscores
        inventory[g_correct] = inventory[group]
        inventory.pop(group,None)

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
