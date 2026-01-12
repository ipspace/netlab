#
# Create device configuration files
#

from pathlib import Path

from box import Box

from ..augment import devices, groups, nodes
from ..providers import SHARED_PREFIX, SHARED_SUFFIX, get_provider_module
from ..utils import log, strings, templates
from . import _TopologyOutput, check_writeable
from . import common as output_common


class ConfigurationFiles(_TopologyOutput):

  DESCRIPTION :str = 'Create device configuration files'

  def write(self, topology: Box) -> None:

    def do_config(t_name: str, f_name: str) -> bool:
      return templates.create_config_file(
        node=n_data,
        node_dict=node_dict,
        topology=topology,
        module=t_name,
        provider_path=provider_path,
        output_path=node_files,
        output_file=f_name)

    check_writeable('device configuration files')

    # Creates a "ghost clean" topology after transformation
    # (AKA, remove unmanaged devices)
    topology = output_common.create_adjusted_topology(nodes.ghost_buster(topology),ignore=[],template_vars=True)
    shared_list = []
    node_files = Path('node_files')
    if 'unprovisioned' in topology.groups:
      unprovisioned = groups.group_members(topology,'unprovisioned')
    else:
      unprovisioned = []

    for n_name,n_data in topology.nodes.items():
      n_provider = devices.get_provider(n_data,topology.defaults)
      p = get_provider_module(topology,n_provider)
      provider_path = p.get_full_template_path()
      node_dict = templates.template_node_data(n_data,topology)       # The dictionary used in templates

      create_list = []
      skip_config = n_data.get('skip_config',[])
      for cfg_item in n_data.get(f'{n_provider}.config_templates',[]):
        cfg_source = cfg_item.source
        if cfg_source in skip_config:
          continue
        if cfg_item.get('mode','') == SHARED_SUFFIX:
          if cfg_source in shared_list:
            create_list.append(f'{cfg_source} (shared)')
            continue

          shared_list.append(cfg_source)
          if do_config(cfg_source,SHARED_PREFIX+cfg_source):
            create_list.append(cfg_source)
        else:
          if do_config(cfg_source,f'{n_name}/{cfg_source}'):
            create_list.append(cfg_source)

      if n_name in unprovisioned:
        continue

      mod_list = ['initial']
      if devices.get_device_attribute(n_data,'features.initial.normalize',topology.defaults):
        mod_list = ['normalize'] + mod_list

      mod_list += n_data.get('module',[]) + n_data.get('config',[])
      for module in mod_list:
        if module in skip_config:
          continue
        if module in create_list:
          continue
        if do_config(module,f'{n_name}/{module}'):
          create_list.append(module)

      if not log.VERBOSE and create_list:
        strings.print_colored_text(strings.pad_err_code('CONFIG',10),'green')
        print(f"{n_name}: {','.join(create_list)}")
