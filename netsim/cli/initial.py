#
# netlab initial command
#
# Deploys initial device configurations
#
import typing

from .. import devices
from ..utils import log
from ..utils import status as _status
from . import (
  ansible,
  external_commands,
  get_message,
  initial_actions,
  lab_status_change,
  load_snapshot,
)


def run_initial(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_actions.initial_config_parse(cli_args)
  topology = load_snapshot(args)

  rest = rest + initial_actions.ansible_args(args)
  deploy_parts = initial_actions.get_deploy_parts(args)

  if args.logging or args.verbose:
    print("Ansible playbook args: %s" % rest)

  ansible.check_version()
  if args.output:
    initial_actions.configs.run(topology,args,rest)
    return
  elif args.ready:
    ansible.playbook('device-ready.ansible',rest)
    if topology:
      lab_status_change(topology,'devices are ready')
  else:
    external_commands.LOG_COMMANDS = True
    deploy_text = ', '.join(deploy_parts) or 'complete configuration'
    if topology is not None:
      devices.process_config_sw_check(topology)
      lab_status_change(topology,f'deploying configuration: {deploy_text}')

    ansible.playbook('initial-config.ansible',rest)
    if topology and not args.no_message:
      message = get_message(topology,'initial',True)
      if message:
        print(f"\n\n{message}")
      lab_status_change(topology,f'configuration deployment complete')

  if _status.is_directory_locked():                   # If we're using the lock file, touch it after we're done
    _status.lock_directory()                          # .. to have a timestamp of when the lab was started

  log.repeat_warnings('netlab initial')

def run(cli_args: typing.List[str]) -> None:
  try:
    run_initial(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab initial')
