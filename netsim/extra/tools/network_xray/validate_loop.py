"""
Background loop started by the network_xray tool plugin:

  python3 validate_loop.py <interval> <max_hours> <out.json> <pid file> <netlab command ...>

Runs '<netlab command> validate --format json' in the current (lab) directory every <interval> seconds
and writes the results to <out.json> (through <out.json>.tmp and a rename, so a reader never sees a
partially written file).

Stops when netlab.snapshot.pickle disappears (the lab is gone), after <max_hours> hours, after 20 failed
runs in a row, or when the pid file no longer contains its process ID. Removes the pid file when it
stops (if the file still contains its process ID).
"""

import json
import os
import subprocess
import sys
import time


def owner_ok(pid_file: str) -> bool:
  try:
    with open(pid_file) as f:
      return int(f.read().strip()) == os.getpid()
  except (OSError, ValueError):
    return False


def run() -> None:
  interval, max_hours = float(sys.argv[1]), float(sys.argv[2])
  out_file, pid_file = sys.argv[3], sys.argv[4]
  netlab = sys.argv[5:]
  end = time.time() + max_hours * 3600
  fails = 0

  time.sleep(1)  # Give the plugin time to write the pid file
  while time.time() < end and os.path.exists("netlab.snapshot.pickle") and owner_ok(pid_file):
    start = time.time()
    results = None
    try:
      r = subprocess.run(
        netlab + ["validate", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=max(60, interval * 6),
      )
      err = f"exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}"
      results = json.loads(r.stdout)
    except subprocess.TimeoutExpired:
      err = "timeout"
    except ValueError:
      pass
    if results is None:
      fails += 1
      print(time.strftime("%H:%M:%S"), f"netlab validate did not print JSON ({err})", flush=True)
      if fails >= 20:
        break
    else:
      out = {
        "netlab_validate": results,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "exit_status": r.returncode,
        "interval": interval,
      }
      with open(out_file + ".tmp", "w") as f:
        json.dump(out, f)
      os.replace(out_file + ".tmp", out_file)
      fails = 0
    time.sleep(max(0.0, interval - (time.time() - start)))


def main() -> None:
  pid_file = sys.argv[4]
  try:
    run()
  finally:
    if owner_ok(pid_file):  # Do not remove the pid file of another loop
      os.remove(pid_file)
    print(time.strftime("%H:%M:%S"), "stopped", flush=True)


if __name__ == "__main__":
  main()
