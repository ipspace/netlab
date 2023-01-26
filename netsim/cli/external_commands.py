#
# Run external commands from netlab CLI
#
import typing
import argparse
import os
import glob
import subprocess
import shutil

from box import Box
from pathlib import Path

from .. import common

def print_step(n: int, txt: str, spacing: typing.Optional[bool] = False) -> None:
  if spacing:
    print()
  print("Step %d: %s" % (n,txt))
  print("=" * 60)

def stringify(cmd : typing.Union[str,list]) -> str:
  if isinstance(cmd,list):
    return " ".join(cmd)
  return str(cmd)

def run_command(cmd : typing.Union[str,list], check_result : bool = False) -> bool:
  if common.debug_active('cli'):
    print("Not running: %s" % cmd)
    return True

  if common.VERBOSE:
    print(".. executing: %s" % cmd)

  if isinstance(cmd,str):
    cmd = [ arg for arg in cmd.split(" ") if arg not in (""," ") ]

  try:
    result = subprocess.run(cmd,capture_output=check_result,check=True,text=True)
    if not check_result:
      return True
    return result.stdout != ""
  except Exception as ex:
    if not common.QUIET:
      print( f"Error executing {stringify(cmd)}:\n  {ex}" )
    return False

def test_probe(p : str) -> bool:
  return run_command(p,True)

def set_ansible_flags(cmd : list) -> list:
  if common.VERBOSE:
    cmd.append("-" + "v" * common.VERBOSE)

  if common.QUIET:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  return cmd

def run_probes(settings: Box, provider: str, step: int = 0) -> None:
  if step:
    print_step(step,"Checking virtualization provider installation",spacing = True)
  elif common.VERBOSE:
    print("Checking virtualization provider installation")
  for p in settings.providers[provider].probe:
    if not test_probe(p):
      common.fatal("%s failed, aborting" % p)
  if common.VERBOSE or step:
    print(".. all tests succeeded, moving on\n")

def start_lab(settings: Box, provider: str, step: int = 2, cli_command: str = "test", exec_command: typing.Optional[str] = None) -> None:
  if exec_command is None:
    exec_command = settings.providers[provider].start
  print_step(step,f"starting the lab -- {provider}: {exec_command}")
  if not run_command(exec_command):
    common.fatal(f"{exec_command} failed, aborting...",cli_command)

def deploy_configs(step : int = 3, command: str = "test", fast: typing.Optional[bool] = False) -> None:
  print_step(step,"deploying initial device configurations",spacing = True)
  cmd = ["netlab","initial"]
  if common.VERBOSE:
    cmd.append("-" + "v" * common.VERBOSE)

  if os.environ.get('NETLAB_FAST_CONFIG',None) or fast:
    cmd.append("--fast")

  if not run_command(set_ansible_flags(cmd)):
    common.fatal("netlab initial failed, aborting...",command)

def custom_configs(config : str, group: str, step : int = 4, command: str = "test") -> None:
  print_step(step,"deploying custom configuration template %s for group %s" % (config,group))
  cmd = ["netlab","config",config,"--limit",group]

  if not run_command(set_ansible_flags(cmd)):
    common.fatal("netlab config failed, aborting...",command)

def stop_lab(settings: Box, provider: str, step: int = 4, command: str = "test", exec_command: typing.Optional[str] = None) -> None:
  print_step(step,"stopping the lab",True)
  if exec_command is None:
    exec_command = settings.providers[provider].stop
  if not run_command(exec_command):
    common.fatal(f"{exec_command} failed, aborting...",command)
