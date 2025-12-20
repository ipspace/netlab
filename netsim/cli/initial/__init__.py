#
# netlab initial command
#
# Deploys initial device configurations
#
import os
import typing

from ... import devices
from ...utils import log
from ...utils import status as _status
from .. import ansible, error_and_exit, external_commands, get_message, lab_status_change, load_snapshot
from . import configs, deploy, utils


def run_initial(cli_args: typing.List[str]) -> None:
  (args,rest) = utils.initial_config_parse(cli_args)
  cwd = os.getcwd()
  topology = load_snapshot(args)

  log.set_logging_flags(args)
  if args.logging or args.verbose:
    print(f"Unrecognized Ansible playbook args: {rest}")

  if args.output:
    if rest:
      error_and_exit(
        'Extra Ansible arguments cannot be used with the --output option',
        more_data=[' '.join(rest)])
    configs.run(topology,args,cwd)
    return
  elif args.ready:
    rest += utils.ansible_args(args)
    ansible.check_version()
    ansible.playbook('device-ready.ansible',rest)
    if topology:
      lab_status_change(topology,'devices are ready')
  else:
    rest += utils.ansible_args(args)
    ansible.check_version()
    deploy.run(topology,args,rest)

  if _status.is_directory_locked():                   # If we're using the lock file, touch it after we're done
    _status.lock_directory()                          # .. to have a timestamp of when the lab was started

  log.repeat_warnings('netlab initial')

def run(cli_args: typing.List[str]) -> None:
  try:
    run_initial(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab initial')
