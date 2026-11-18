"""
network_xray tool plugin -- keep 'netlab validate --format json' running while the lab is up,
so the network-xray web page can show the results of the lab validation tests as they change.

The plugin is loaded whenever the network_xray tool is active (see the 'plugin' attribute in
netsim/tools/network_xray.yml and docs/dev/extools.md).

The validation loop is opt-in: it runs only when 'tools.network_xray.validate' is set to True.
Use 'tools.network_xray.plugin: []' to remove the plugin.

* 'netlab up' (after the tools have been started): start a background process that runs
  'netlab validate --format json' in the lab directory every 'tools.network_xray.validate_interval'
  seconds (default: 30) and writes the results into network_xray/validate.json
* 'netlab down' (before the lab is stopped): stop the background process
* 'netlab down --cleanup': remove the files created by the plugin

The plugin uses the plugin CLI hooks; it does not change the user CLI hooks. The background process
also stops when the lab snapshot disappears, after 'tools.network_xray.validate_max_hours' hours
(default: 12), or after 20 failed 'netlab validate' runs in a row.

The plugin does nothing when 'netlab up' or 'netlab down' is started with '--dry-run'.
"""

import math
import os
import signal
import subprocess
import sys

from box import Box

from netsim import cli, data
from netsim.utils import log

TOOL = "network_xray"
PLUGIN = "tools.network_xray"  # The name netlab uses to load this plugin
OUT_DIR = "network_xray"
PID_FILE = os.path.join(OUT_DIR, "validate.pid")
OUT_FILE = os.path.join(OUT_DIR, "validate.json")
LOG_FILE = os.path.join(OUT_DIR, "validate.log")
LOOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_loop.py")


def tool_settings(topology: Box) -> Box:
  return topology.get(f"tools.{TOOL}", {})


def loop_wanted(topology: Box) -> bool:
  return tool_settings(topology).get("validate", False) is True


def positive_number(settings: Box, name: str, default: float) -> float:
  value = settings.get(name, default)
  if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0:
    return value
  log.warning(text=f"tools.{TOOL}.{name} must be a positive number, using the default value ({default})", module=TOOL)
  return default


"""
Register the plugin for the 'netlab up' and 'netlab down' plugin CLI hooks when the user asked for the
validation loop
"""


def post_transform(topology: Box) -> None:
  if not loop_wanted(topology):
    return
  for cmd in ("up", "down"):
    if PLUGIN not in topology.defaults.netlab[cmd].get("plugin", []):
      data.append_to_list(topology.defaults.netlab[cmd], "plugin", PLUGIN)


def running_pid() -> int:
  try:
    with open(PID_FILE) as f:
      pid = int(f.read().strip())
    os.kill(pid, 0)
    if os.path.isdir("/proc"):  # Make sure the process is still our loop (process IDs get reused)
      with open(f"/proc/{pid}/cmdline", "rb") as f:
        if LOOP.encode() not in f.read():
          return 0
    return pid
  except (OSError, ValueError):
    return 0


def post_shell_post_tools_start(topology: Box) -> None:
  if not loop_wanted(topology):
    return
  if cli.is_dry_run():
    print(f"DRY RUN: start the {TOOL} 'netlab validate' loop")
    return
  if running_pid():  # The loop is already running (for example, 'netlab up' after a failed start)
    return

  os.makedirs(OUT_DIR, exist_ok=True)
  settings = tool_settings(topology)
  interval = positive_number(settings, "validate_interval", 30)
  max_hours = positive_number(settings, "validate_max_hours", 12)
  netlab_cmd = [cli.NETLAB_SCRIPT or "netlab"]  # The netlab command that started this lab
  with open(LOG_FILE, "a") as logf:
    p = subprocess.Popen(
      [sys.executable, LOOP, str(interval), str(max_hours), OUT_FILE, PID_FILE] + netlab_cmd,
      stdout=logf,
      stderr=logf,
      stdin=subprocess.DEVNULL,
      start_new_session=True,
    )
  with open(PID_FILE, "w") as f:
    f.write(str(p.pid))
  log.info(text=f"'netlab validate' runs every {interval} seconds, results in {OUT_FILE}", module=TOOL)


def pre_shell_pre_stop_lab(topology: Box) -> None:
  if cli.is_dry_run():
    print(f"DRY RUN: stop the {TOOL} 'netlab validate' loop")
    return
  pid = running_pid()
  if pid:
    try:
      os.killpg(pid, signal.SIGTERM)
    except OSError:
      pass
  if os.path.exists(PID_FILE):
    os.remove(PID_FILE)


def post_shell_post_cleanup(topology: Box) -> None:
  if cli.is_dry_run():
    print(f"DRY RUN: remove the {TOOL} validation files")
    return
  for fname in (OUT_FILE, OUT_FILE + ".tmp", LOG_FILE, PID_FILE):
    if os.path.exists(fname):
      os.remove(fname)
  if os.path.isdir(OUT_DIR) and not os.listdir(OUT_DIR):
    os.rmdir(OUT_DIR)
