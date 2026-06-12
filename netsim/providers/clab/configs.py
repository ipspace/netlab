#
# Containerlab provider module
#
import pathlib
import typing

from box import Box

from ...augment import devices
from ...cli import external_commands
from ...data import append_to_list
from ...utils import log, strings
from . import utils

'''
add_default_config_mode: if the netlab_config_mode is set, add configured modules to _node_config dictionary
'''
def add_default_config_mode(node: Box, topology: Box) -> None:
  cfg_mode = devices.get_node_group_var(node,'netlab_config_mode',topology.defaults)
  if not cfg_mode:
    return

  d_features = devices.get_device_features(node,topology.defaults)
  if cfg_mode not in d_features.get('initial.config_mode',[]):
    log.error(
      f'Configuration mode {cfg_mode} is not valid for device {node.device} (node {node.name})',
      module='clab',
      category=log.IncorrectValue)

  # Get what's already been processed and the list of configuration snippets. That list
  # has to include initial configuration, all modules, and custom config templates
  #
  features = devices.get_device_features(node,topology.defaults)
  mod_list = ['normalize'] if features.initial.get('normalize',False) else []
  mod_list += ['initial'] + node.get('module',[]) + node.get('config',[])
  node_cfg = node.get('_node_config',{}) + node.get('_daemon_config',{})
  node_cfg_path = devices.get_node_group_var(node,'netlab_config_path',topology.defaults)
  for idx,m in enumerate(mod_list,start=1):
    append_to_list(node,'netlab_ansible_skip_module',m)
    m = m.replace('.','@')                        # Use the @-as-. hack for things like bgp.session
    if m in node_cfg:                             # Module already processed, move on
      continue
    file_target = ''                              # By default, config file is not accessible in the container
    if cfg_mode == 'sh':                          # File mapped into container using a containerlab bind
      cfg_path = node_cfg_path or '/etc/config/'
      file_target = f'{cfg_path}{idx:02d}-{m}.sh'
    elif cfg_mode == 'cp_sh':                     # File copied into container, must use existing directory
      cfg_path = node_cfg_path or '/etc/cfg-'
      file_target = f'{cfg_path}-{idx:02d}-{m}.sh'

    # Finally, store the mapping of this config item into _node_config
    node._node_config[m] = f'{file_target}:{cfg_mode}'

  # Finally, if the container needs extra precautions to work with config mode (hi there, FRR),
  # add the exec commands to the container exec list
  utils.add_clab_exec(node,'netlab_config_exec',topology)

'''
Get all configuration snippets with the specified mode
'''
def get_templates_with_mode(n: Box, mode: typing.Optional[str]) -> list:
  return [ item for item in n.get('clab.config_templates',[])   # Collect config template items
              if 'mode' in item and                             # ... that have mode set
                 (item.mode == mode or mode is None) ]          # ... and match the requested mode (None == all modes)

'''
Add startup configuration point if the node has config_templates with 'startup' mode
'''
def add_startup_config(n: Box) -> None:
  if not get_templates_with_mode(n,'startup'):
    return
  n.clab['startup-config'] = f'node_files/{n.name}/startup.partial.config'

'''
Generate node startup configuration from configuration snippets with 'startup' mode
in node_files/node folder into the file specified in n.clab.startup-config
'''
def generate_startup_config(n: Box) -> None:
  startup_snippets = get_templates_with_mode(n,'startup')
  if not startup_snippets:                        # No startup config snippets
    return

  startup_path = n.clab['startup-config']
  try:
    with pathlib.Path(startup_path).open("w") as startup_cfg:
      for item in startup_snippets:
        startup_cfg.write(pathlib.Path(f"node_files/{n.name}/{item.source}").read_text())
        startup_cfg.write("\n")
  except Exception as ex:
    log.error(
      f'Cannot open/write startup configuration file {startup_path}',
      more_data=[ str(ex) ],
      module='clab')
    return

  if not log.QUIET:
    log.status_created()
    print(f"startup configuration for {n.name}",flush=True)

def  deploy_container_config(node: Box, node_name: str, deploy_list: list) -> None:
  for cfg_item in node.clab.config_templates:                 # Go through configuration files (we know they exist)
    mod_name = cfg_item.source                                # Get module name
    f_type = cfg_item.get('mode',None)
    if mod_name not in deploy_list:                           # ... and skip it if we're not deploying it
      continue
    if f_type == 'cp_sh' and cfg_item.target:                 # Note: checking for non-existent attribute is OK
      cp_status = external_commands.run_command(
                    cmd=['docker','cp','-q',
                          f'node_files/{node.name}/{cfg_item.source}',
                          f'{node_name}:{cfg_item.target}'],
                    ignore_errors=True)
      if not cp_status:
        log.error(
          f'Cannot copy configuration file {cfg_item.source} into container {node_name} as {cfg_item.target}',
          category=log.FatalError,
          module='clab',
          skip_header=True)
        continue
      elif log.VERBOSE:
        log.info(f'Copying {mod_name} configuration into {node_name} as {cfg_item.target}')

    config_cmd = None                                         # Command to execute
    if f_type == 'ns':                                        # Is this a host-side script?
      config_cmd = f'sudo ip netns exec {node_name} sh node_files/{node.name}/{mod_name}' 
      log.info(f'Executing {mod_name} configuration for node {node.name} (namespace {node_name})')
    elif f_type in ('sh','cp_sh'):
      if not cfg_item.target:
        log.error(
          f'Internal error: bash script for module {mod_name} is not mapped into a container file',
          more_data = [f'node: {node.name} / device: {node.device}'],
          category=log.FatalError,
          module='clab')
        break
      config_cmd = f'docker exec {node_name} {cfg_item.target}' # Container-side script
      log.info(f'Executing {mod_name} configuration for node {node.name}')
    elif f_type == 'startup':                                 # Is this part of startup config?
      append_to_list(node._deploy,'startup',mod_name)

    if not config_cmd:                                        # Not an executable file?
      continue

    status = external_commands.run_command(
                config_cmd,                                   # Execute config command
                ignore_errors=True,
                check_result=True,                            # Capture stdout
                return_exitcode=True)                         # and return exit code
    if status == 0:                                           # Everything OK?
      append_to_list(node._deploy,'success',mod_name)
    else:                                                     # Otherwise we failed
      printout = ''                                           # Collect any printout we might have received
      if external_commands.CAPTURED_STDOUT:                   # ... making sure it ends with a single newline
        stdout = external_commands.CAPTURED_STDOUT.strip(" \n") + "\n"
        printout +='  '+strings.wrap_error_message(stdout,indent=2)
      if external_commands.CAPTURED_STDERR:
        stderr = external_commands.CAPTURED_STDERR.strip(" \n") + "\n"
        printout +='  '+strings.wrap_error_message(stderr,indent=2)
      if printout:                                            # And print it
        strings.print_colored_text(txt=printout,color='bright_black')
      log.error(
        f'{mod_name} configuration in namespace {node_name} failed for node {node.name}',
        category=log.FatalError,
        more_data=f'Executed command: {config_cmd}',
        skip_header=True,
        module='initial')
      append_to_list(node._deploy,'failed',mod_name)
      break