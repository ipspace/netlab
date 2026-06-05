"""
Implement hooks executed by CLI commands

netlab CLI commands can execute two types of hooks:

* CLI hooks -- system commands (usually Bash scripts)
* Plugin hooks -- plugin calls executed after the data transformation
  has completed.

The hooks are registered in the netlab[command] system defaults:

* Plugin hooks are registered in the 'plugin' list. All plugins are
  examined for every hook.
* CLI hooks are registered in the _hook_ string. A single CLI command
  can be executed for every hook.
"""
from box import Box

from ..augment import plugin as a_plugin
from ..utils import log
from .external_commands import run_command

P_CACHE: dict = {}            # Use a cache to optimize plugin loading 

def cli_plugin_hooks(topology: Box, cli_command: str, hook: str) -> None:
  """
  Iterate over plugins that registered the comamnd hook
  
  Note: we're caching the loaded plugins to avoid repeated attempts
  to load the same plugins. We cannot use the original 'Plugin'
  dictionary as it's removed as the last step in the topology
  transformation process
  """
  global P_CACHE
  p_list = topology.defaults.get(f'netlab.{cli_command}.plugin',[])
  if log.VERBOSE >= 3:
    print(f"CLI command {cli_command} plugin hooks: {p_list} hook: {hook}")
  for p_name in p_list:
    if p_name in P_CACHE:                                   # Have we tried to load the plugin before?
      p_module = P_CACHE[p_name]                            # Use the previous result
    else:
      p_module = a_plugin.load_plugin(p_name,topology)      # Try to load the plugin
      P_CACHE[p_name] = p_module                            # And cache whatever we got (including the failure)
      if log.VERBOSE >= 3:
        if p_module:
          print(f"Loaded CLI hook plugin {p_name}")
        else:
          print(f"Failed to load CLI hook plugin {p_name}")

    if p_module:                                            # Did we succeed in loading the plugin?
      a_plugin.execute_plugin_hook(hook,p_module,topology)  # Try to execute the relevant plugin hook

def cli_shell_hooks(settings: Box, cli_command: str, hook: str) -> None:
  hook_key = f'netlab.{cli_command}.{hook}'
  cmd = settings.get(hook_key,None)
  if log.VERBOSE >= 2:
    print(f"CLI hook {hook_key}: {cmd}")
  if not cmd:
    return
  if log.VERBOSE:
    log.info(f'Running {hook} CLI hook',module=cli_command,more_data=[cmd])
  if not run_command(cmd):
    log.fatal(f'CLI hook {hook} returned an error, aborting...',cli_command)

def run_cli_hooks(topology: Box, cli_command: str, hook: str) -> None:
  cli_plugin_hooks(topology,cli_command,'pre_shell_'+hook)
  cli_shell_hooks(topology.defaults,cli_command,hook)
  cli_plugin_hooks(topology,cli_command,'post_shell_'+hook)
