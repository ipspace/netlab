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

def test_probe(p : str) -> bool:
  args = p.split(" ")
  try:
    result = subprocess.run(args,capture_output=True,check=True,text=True)
    return result.stdout != ""
  except:
    return False

def run_probes(settings: Box, provider: str) -> None:
  if common.VERBOSE:
    print("Checking virtualization provider installation")
  for p in settings.providers[provider].probe:
    if common.VERBOSE:
      print(".. executing: %s" % p)
    if not test_probe(p):
      common.fatal("%s failed, aborting" % p)
  if common.VERBOSE:
    print(".. all tests succeeded, moving on\n")

def start_lab(settings: Box, provider: str, step: int = 2) -> None:
  print_step(step,"starting the lab",True)
  cmd = settings.providers[provider].start
  try:
    subprocess.run(cmd.split(" "),check=True)
  except:
    common.fatal("%s failed, aborting..." % cmd,"test")

def deploy_configs(step : int = 3) -> None:
  print_step(step,"deploying initial device configurations")
  cmd = ["netlab","initial"]
  if common.VERBOSE:
    cmd.append("-v")
  try:
    subprocess.run(cmd,check=True)
  except:
    common.fatal("netlab initial failed, aborting...","test")

def stop_lab(settings: Box, provider: str, step: int = 4) -> None:
  print_step(step,"stopping the lab",True)
  cmd = settings.providers[provider].stop
  try:
    subprocess.run(cmd.split(" "),check=True)
  except:
    common.fatal("%s failed, aborting..." % cmd,"test")
