#
# Ansible functions for the netlab validate command
#
# The 'ansible' validation action fetches device state by running a show command
# through an Ansible module (network_cli), for devices whose CLI cannot be driven
# by netlab's SSH/docker validation transports -- e.g. IP Infusion OcNOS, whose
# restricted `cmlsh` rejects every non-interactive SSH command. It is a validation
# data *source*, a peer of suzieq.py (netsim/cli/validate/suzieq.py), not a device
# connection method.
#
# A test selects it with an `ansible` action (or a plugin `ansible_<test>` function)
# that supplies the show command; the device supplies the module in
#   defaults.devices.<device>.netlab_validate.ansible_module
# The result is parsed as JSON when the command emits JSON (e.g. `... | json`), so a
# `valid:` expression can use structured data; otherwise the raw CLI text is returned
# as `_result.stdout` for a plugin valid_<test>() to screen-scrape.
#
import json
import shlex
import subprocess
import typing

from box import Box

from ... import data
from ...utils import log
from . import report, utils


def get_result(v_entry: Box, n_name: typing.Optional[str], topology: Box, verbosity: int) -> Box:
  err_value = data.get_box({'_error': True})
  if not n_name:
    return err_value
  node = topology.nodes[n_name]

  v_cmd = utils.get_exec_list(v_entry, 'ansible', node, topology)   # command tokens
  if not v_cmd:
    log.error(
      f'Test {v_entry.name}: no ansible show command for {n_name}/{node.device}',
      category=log.MissingValue, module='validation')
    return err_value
  command = ' '.join(v_cmd)

  a_module = topology.defaults.devices[node.device].netlab_validate.ansible_module
  if not a_module:
    log.error(
      f'Device {node.device} has no netlab_validate.ansible_module; cannot use the ansible validation action',
      category=log.MissingValue, module='validation')
    return err_value

  # Build the module arguments. Networking "<os>_command" modules take the show
  # command in a `commands` argument, passed as a single quoted string (ansible
  # ad-hoc rejects a bare list literal: "does not support raw params"). The plain
  # command/shell modules take the bare command line instead; other argument shapes
  # can be added here later if a device needs them.
  if str(a_module).split('.')[-1] in ('command', 'shell'):
    module_args = command
  else:
    module_args = 'commands=%r' % command

  # Reuse the netlab-generated inventory (hosts.yml + ansible.cfg in the lab dir).
  cmd = ['ansible', n_name, '-m', str(a_module), '-a', module_args, '--one-line']
  cmd_str = shlex.join(cmd)

  # On any failure, surface the exact command so the user can run it by hand to see
  # what went wrong (mirrors execute_netlab_config in netsim/cli/validate/devices.py).
  def _fail(msg: str, detail: typing.Optional[str] = None) -> Box:
    hint = f'Run the command manually to inspect the device output:\n  {cmd_str}'
    if detail:
      hint = f'{str(detail).rstrip()}\n\n{hint}'
    report.log_failure(msg, topology, more_data=hint)
    return err_value

  if verbosity >= 3:
    print(f'Preparing to execute {command!r} on {n_name} via Ansible ({a_module})')

  try:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
  except Exception as ex:                                   # noqa: BLE001
    return _fail(f'Ansible action failed for "{command}" on {n_name}', str(ex))

  raw = out.stdout or ''
  # ansible --one-line: "<host> | SUCCESS => { ...json... }" (or FAILED!/UNREACHABLE!)
  if ' => ' not in raw:
    return _fail(f'Ansible action returned no parseable result for "{command}" on {n_name}',
                 raw or out.stderr)
  status, _, payload = raw.partition(' => ')
  try:
    a_result = json.loads(payload)
  except Exception as ex:                                   # noqa: BLE001
    return _fail(f'Cannot parse the Ansible result for "{command}" on {n_name}', str(ex))
  if 'SUCCESS' not in status:
    return _fail(f'Ansible command "{command}" failed on {n_name}', a_result.get('msg') or raw)

  if verbosity >= 3:
    print(f'Executed {command!r}, got {a_result}')

  stdout = a_result.get('stdout', '')
  text = '\n'.join(stdout) if isinstance(stdout, list) else str(stdout)

  # If the device emitted JSON (e.g. `show ... | json`), hand structured data to the
  # valid: expression; otherwise return the raw text for a valid_<test>() to parse.
  parsed = utils.parse_JSON(text)
  if isinstance(parsed, Exception):
    return data.get_box({'stdout': text})
  return parsed
