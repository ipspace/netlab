#
# Run external commands from netlab CLI
#
import typing
import os
import subprocess
from box import Box

from . import is_dry_run
from ..utils import strings,log

def print_step(n: int, txt: str, spacing: typing.Optional[bool] = False) -> None:
  if spacing:
    print()
  print("Step %d: %s" % (n,txt))
  print("=" * 72)

def stringify(cmd : typing.Union[str,list]) -> str:
  if isinstance(cmd,list):
    return " ".join(cmd)
  return str(cmd)

"""
add_netlab_path: Prepend the directory from which the current copy of netlab was ran to the search path
"""
def add_netlab_path() -> None:
  from . import NETLAB_SCRIPT

  netlab_path = os.path.dirname(NETLAB_SCRIPT)
  path = os.environ['PATH']
  if netlab_path in path:
    return

  if log.VERBOSE or log.debug_active('external'):
    print(f"Adding {netlab_path} to system PATH")
  os.environ['PATH'] = netlab_path + ":" + os.environ['PATH']

  if log.VERBOSE or log.debug_active('external'):
    print(f"New system path: {os.environ['PATH']}")

  return

"""
run_command: Execute an external command specified as a string or a list of CLI parameters

Flags:
* check_result -- return False if the command does not produce any output
* ignore_errors -- do not print errors to the console
* return_stdout -- return the command output instead of True/False
"""
def run_command(
    cmd : typing.Union[str,list],
    check_result : bool = False,
    ignore_errors: bool = False,
    return_stdout: bool = False) -> typing.Union[bool,str]:

  if log.debug_active('cli'):
    print(f"Not running: {cmd}")
    return True

  if is_dry_run():
    print(f"DRY RUN: {cmd}")
    return True

  if log.VERBOSE or log.debug_active('external'):
    print(f"run_command executing: {cmd}")

  add_netlab_path()
  if isinstance(cmd,str):
    cmd = [ arg for arg in cmd.split(" ") if arg not in (""," ") ]

  if not cmd:                                               # Skip empty commands
    return True

  try:
    result = subprocess.run(cmd,capture_output=check_result,check=True,text=True)
    if log.debug_active('external') or log.VERBOSE >= 3:
      print(f'... run result: {result}')
    if not check_result:
      return True
    if return_stdout:
      return result.stdout
    return result.stdout != ""
  except Exception as ex:
    if not log.QUIET and not ignore_errors:
      print(f"Error executing {stringify(cmd)}:\n  {ex}")
    return False

def test_probe(p : typing.Union[str,list,Box],quiet : bool = False) -> bool:
  if isinstance(p,str):
    return bool(run_command(p,check_result=True,ignore_errors=quiet))

  elif isinstance(p,list):
    for p_item in p:
      if not test_probe(p_item,quiet):
        return False
    return True

  elif isinstance(p,Box):
    OK = bool(run_command(p.cmd,check_result=True,ignore_errors=True))
    if not OK and not quiet:
      log.fatal(p.err)
    return OK

  else:
    log.fatal(f"Internal error: invalid probe specification: {p}")
    return False

def set_ansible_flags(cmd : list) -> list:
  if log.VERBOSE:
    cmd.append("-" + "v" * log.VERBOSE)

  if log.QUIET:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  return cmd

def run_probes(settings: Box, provider: str, step: int = 0) -> None:
  if step:
    print_step(step,f"Checking virtualization provider installation: {provider}",spacing = True)
  elif log.VERBOSE:
    print("Checking virtualization provider installation")
  for p in settings.providers[provider].probe:
    if not test_probe(p):
      log.fatal("%s failed, aborting" % p)
  if not is_dry_run() and not log.QUIET:
    log.status_success()
    print(f'{provider} installed and working correctly')

def start_lab(settings: Box, provider: str, step: int = 2, cli_command: str = "test", exec_command: typing.Optional[str] = None) -> None:
  if exec_command is None:
    exec_command = settings.providers[provider].start
  print_step(step,f"starting the lab -- {provider}: {exec_command}")
  if not run_command(exec_command):
    log.fatal(f"{exec_command} failed, aborting...",cli_command)

def deploy_configs(command: str = "test", fast: typing.Optional[bool] = False) -> None:
  cmd = ["netlab","initial","--no-message"]
  if log.VERBOSE:
    cmd.append("-" + "v" * log.VERBOSE)

  if os.environ.get('NETLAB_FAST_CONFIG',None) or fast:
    cmd.append("--fast")

  if not run_command(set_ansible_flags(cmd)):
    log.fatal("netlab initial failed, aborting...",command)

  log.status_success()
  print("Lab devices configured")

def custom_configs(config : str, group: str, step : int = 4, command: str = "test") -> None:
  print_step(step,"deploying custom configuration template %s for group %s" % (config,group))
  cmd = ["netlab","config",config,"--limit",group]

  if not run_command(set_ansible_flags(cmd)):
    log.fatal("netlab config failed, aborting...",command)

def stop_lab(settings: Box, provider: str, command: str = "test", exec_command: typing.Optional[str] = None) -> None:
  if exec_command is None:
    exec_command = settings.providers[provider].stop
  if not run_command(exec_command):
    log.fatal(f"{exec_command} failed, aborting...",command)

"""
Get a runtime-related parameter for a tool
"""
def get_tool_runtime_param(tool: str, param: str, verbose: bool, topology: Box) -> typing.Optional[typing.Any]:
  tdata = topology.defaults.tools[tool] + topology.tools[tool]
  runtime = tdata.runtime or 'docker'
  if not runtime in tdata:
    if verbose:
      print(f"... skipping {tool} tool, no {runtime} runtime configuration")
    return None

  tdata = tdata[runtime] + tdata
  topology[tool] = tdata                       # Enable 'tool.param' syntax in tool commands
  if not tdata[param]:
    if verbose:
      print(f"... skipping {tool} tool, no {runtime} {param} command")
    return None

  return tdata[param]

"""
Get a list of external tool commands to execute
"""
def get_tool_command(tool: str, cmd: str, topology: Box,verbose: bool = True) -> typing.Optional[list]:
  cmds = get_tool_runtime_param(tool,cmd,verbose,topology)
  if cmds is None:
    return None
  
  return cmds if isinstance(cmds,list) else [ cmds ]

"""
Check if the current topology uses docker in any way: does it have clab as primary or secondary provider?
"""
def docker_is_used(topology: Box) -> bool:
  if topology.provider == 'clab':
    return True

  return 'clab' in topology[topology.provider].providers

#
# Execute external tool commands
#
def execute_tool_commands(cmds: list, topology: Box) -> None:
  topology.sys.docker_net = ""
  if docker_is_used(topology):
    topology.sys.docker_net = f"--network={topology.addressing.mgmt.get('_network',None) or 'netlab_mgmt'}"

  for cmd in cmds:
    cmd = strings.eval_format(cmd,topology)
    run_command(cmd = [ 'bash', '-c', cmd ],check_result=True)

#
# Get the "how to connect to the tool" message
#
def get_tool_message(tool: str, topology: Box) -> typing.Optional[str]:
  msg = get_tool_runtime_param(tool,'message',False,topology)
  if msg is None:
    return None

  return strings.eval_format(msg,topology)
