#
# Run external commands from netlab CLI
#
import os
import subprocess
import sys
import typing

from box import Box

from ..data import global_vars
from ..utils import log, strings
from . import is_dry_run, lab_status_log


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
has_command: figures out whether a command is available
"""
def has_command(cmd: str) -> bool:
  return bool(run_command(['bash','-c',f'command -v {cmd}'],check_result=True,ignore_errors=True))

"""
run_command: Execute an external command specified as a string or a list of CLI parameters

Flags:
* check_result -- return False if the command does not produce any output
* ignore_errors -- do not print errors to the console
* return_stdout -- return the command output instead of True/False
"""
LOG_COMMANDS: bool = False

def log_command(cmd: typing.Union[str,list], status: str) -> None:
  global LOG_COMMANDS
  if not LOG_COMMANDS:
    return

  topology = global_vars.get_topology()
  if not topology:
    log.fatal('Internal error: topology not set',module='log_command')
    return

  cmd_text = cmd if isinstance(cmd,str) else ' '.join(cmd)
  lab_status_log(topology,f'{status}: {cmd_text}')

def run_command(
    cmd : typing.Union[str,list],
    check_result : bool = False,
    ignore_errors: bool = False,
    return_stdout: bool = False,
    return_exitcode: bool = False,
    run_always: bool = False) -> typing.Union[bool,int,str]:

  if log.debug_active('cli'):
    print(f"Not running: {cmd}")
    return True

  if is_dry_run():
    if run_always:
      print(f"RUNNING: {cmd}")
    else:
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
    result = subprocess.run(cmd,capture_output=check_result,check=not return_exitcode,text=True)
    if log.debug_active('external') or log.VERBOSE >= 3:
      print(f'... run result: {result}')
    if return_exitcode:
      log_command(cmd,f'FAIL(result.returncode)' if result.returncode else 'OK')
      return result.returncode
    if not check_result:
      log_command(cmd,'OK')
      return True
    if return_stdout:
      log_command(cmd,'OK')
      return result.stdout

    log_command(cmd,'OK' if result.stdout != "" else 'FAIL')
    return result.stdout != ""
  except Exception as ex:
    log_command(cmd,'ERROR')
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
# Get local IP address, either the endpoint of the SSH connection or loopback
#
def get_local_addr() -> str:
  ssh_connection = os.environ.get("SSH_CONNECTION")
  if ssh_connection:
    ssh_list = ssh_connection.split(" ")
    if len(ssh_list) >= 4:
      return ssh_list[2]
    
  return "127.0.0.1"

#
# Execute external tool commands
#
def execute_tool_commands(cmds: list, topology: Box) -> typing.Optional[str]:
  topology.sys.docker_net = ""
  topology.sys.ipaddr = get_local_addr()
  if docker_is_used(topology):
    topology.sys.docker_net = f"--network={topology.addressing.mgmt.get('_network',None) or 'netlab_mgmt'}"

  output = ''
  for cmd in cmds:
    cmd = strings.eval_format(cmd,topology)
    status = run_command(
              cmd = [ 'bash', '-c', cmd + " 2>&1"],   # Redirect STDERR to STDOUT to collect it
              check_result=True,                      # I want to get the status
              ignore_errors=True,                     # ... returned but not reported
              return_stdout=True)                     # ... and we need STDOUT content to look for the warnings
    if not isinstance(status,str):
      log.error(
        f'Failed to execute {cmd}',module='tools',
        category=log.ErrorAbort,
        skip_header=True)
      return None
    else:
      output += status

  return output

#
# Get the "how to connect to the tool" message
#
def get_tool_message(tool: str, topology: Box) -> typing.Optional[str]:
  msg = get_tool_runtime_param(tool,'message',False,topology)
  if msg is None:
    return None

  return strings.eval_format(msg,topology)

#
# Keyboard interrupt handler
#
def interrupted(cmd: str, hint: str = 'interrupt') -> typing.NoReturn:
  print()
  msg = f'{cmd} command was interrupted'
  log.error(
    msg,
    category=log.ErrorAbort,
    module='cli',
    hint=hint,
    skip_header=True)
  topology = global_vars.get_topology()
  if topology is not None:
    lab_status_log(topology,msg)
  sys.exit(1)
