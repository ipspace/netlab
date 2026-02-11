#
# Create Ansible inventory
#
import os
import typing

from box import Box

from ..augment import devices, nodes, plugin
from ..data import get_empty_box
from ..utils import files as _files
from ..utils import log, strings, templates
from . import _TopologyOutput, check_writeable
from .common import adjust_inventory_host, get_host_addresses

forwarded_port_name = { 'ssh': 'ansible_port', }

"""
Build the contents of the 'all' group (shared variables)
"""

def get_all_vars(topology: Box) -> Box:
  all_vars = get_empty_box()
  all_vars.netlab_provider = topology.defaults.provider
  all_vars.netlab_name = topology.name
  all_vars.hosts = get_host_addresses(topology)
  all_vars.netlab_hosts = all_vars.hosts
  if 'paths' in topology.defaults:
    for k,v in topology.defaults.paths.items():
      all_vars[f'paths_{k}'] = v

  for kw in ['prefix']:
    if kw in topology:
      all_vars[kw] = topology[kw]

  if 'addressing' in topology:
    for name,pool in topology.addressing.items():
      for k,v in pool.items():
        if '_pfx' not in k and '_eui' not in k:
          all_vars.pools[name][k] = v

  return all_vars

def create(topology: Box) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  inventory.all.vars = get_all_vars(topology)
  inventory.all.hosts = {}

  # Create placeholders for well-known groups
  #
  for grp in ('modules','custom_configs','daemons','unprovisioned','netlab_no_reload'):
    inventory[grp].hosts = {}

  defaults = topology.defaults

  if 'module' in topology:
    inventory.modules.vars.netlab_module = topology.module

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

    ready = devices.get_node_group_var(node,'netlab_ready',topology.defaults) or []
    for r_item in ready:
      inventory[f'netlab_ready_{r_item}'].hosts[name] = {}

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

def write_inventory_file(data: Box, fname: str, header: str, filetype: typing.Optional[str] = None) -> None:
  if not filetype:
    filetype = 'yaml' if fname.endswith('.yml') or fname.endswith('.yaml') else 'json'
  else:
    fname += '.' + filetype

  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  if filetype in ['yaml','yml']:
    contents = header+"\n"+strings.get_yaml_string(data)
  else:
    contents = data.to_json(indent=2)
  _files.create_file_from_text(fname,contents)

min_inventory_data = [ 'id','ansible_host','ansible_port','ansible_connection','ansible_user','ansible_ssh_pass' ]

def ansible_inventory(
      topology: Box,
      fname: typing.Optional[str] = 'hosts.yml',
      hostvars: typing.Optional[str] = 'dirs',
      filetype: str = 'json') -> None:

  inventory = create(topology)

#  import ipdb; ipdb.set_trace()
  header = "# Ansible inventory created from %s\n#\n" % topology.get('input','<unknown>')

  if not fname:
    fname = 'hosts.yml'
  if not hostvars:
    hostvars = "dirs"

  if hostvars == "min":
    write_inventory_file(inventory,fname,header)
    log.status_created()
    print(f"single-file Ansible inventory {fname}")
    return

  for g in inventory.keys():
    gvars = inventory[g].pop('vars',None)
    if gvars:
      write_inventory_file(gvars,f'group_vars/{g}/topology',header,filetype)
      if not log.QUIET:
        strings.print_colored_text('[GROUPS]  ','bright_cyan','Created ')
        print(f"group_vars for {g}")

    if 'hosts' in inventory[g]:
      hosts = inventory[g]['hosts']
      h_list = []
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

        write_inventory_file(vars_host,f'host_vars/{h}/topology',header,filetype)
        if log.VERBOSE:
          strings.print_colored_text('[HOSTS]   ','bright_cyan','Created ')
          print(f"host_vars for {h}")
        else:
          h_list.append(h)
        hosts[h] = min_host
      
      if not log.QUIET and not log.VERBOSE and h_list:
        strings.print_colored_text('[HOSTS]   ','bright_cyan','Created ')
        text = "host_vars for " + ", ".join(h_list)
        w_text = strings.wrap_text_into_lines(text,strings.rich_width-10,first_line=' '*10,next_line=' '*10)
        w_text[0] = w_text[0][10:]
        print("\n".join(w_text))

  write_inventory_file(inventory,fname,header)
  log.status_created()
  print(f"minimized Ansible inventory {fname}")

def ansible_config(
      config_file: typing.Union[str,None] = 'ansible.cfg',
      inventory_file: typing.Union[str,None] = 'hosts.yml') -> None:
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
    hostfile = self.settings.get('hostfile','hosts.yml')
    configfile = self.settings.get('configfile','ansible.cfg')
    hostvars = self.settings.get('hostvars',None)
    filetype = self.settings.get('filetype','json')

    valid_ftype = ['json','yml','yaml']
    if filetype not in valid_ftype:
      log.fatal(
        f'defaults.outputs.ansible.filetype parameter must have one of these values: {",".join(valid_ftype)}',
        module='ansible')

    if hasattr(self,'filenames'):
      hostfile = self.filenames[0]
      if len(self.filenames) > 1:
        configfile = self.filenames[1]
      if len(self.filenames) > 2:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[2:]),log.IncorrectValue,'ansible')

    if self.format:
      hostvars = self.format[0]
    
    # Creates a "ghost clean" topology
    # (AKA, remove unmanaged devices)
    ansible_topology = nodes.ghost_buster(topology)

    ansible_inventory(ansible_topology,hostfile,hostvars,filetype)
    ansible_config(configfile,hostfile)
