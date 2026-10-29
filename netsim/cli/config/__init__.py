#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing

from ...utils import log
from .. import (
  _nodeset,
  external_commands,
  load_snapshot,
  set_dry_run,
)
from . import config, reload, utils


def run_config(cli_args: typing.List[str]) -> None:
  """
  Deploy a custom configuration template or reload saved device configurations
  """
  (args,rest) = utils.custom_config_parse(cli_args)
  log.set_logging_flags(args)
  set_dry_run(args)
  topology = load_snapshot(args)

  nodeset = _nodeset.from_args(args,topology,skip_unprovisioned=True)
  utils.set_initial_args(args,initial=False)

  if args.reload:
    reload.reload_node_configs(topology,nodeset,args,rest)
  else:
    config.deploy_custom_config(topology,nodeset,args,rest)

  log.repeat_warnings('netlab config')
  if args.reload and topology.get('groups.netlab_no_reload.members',[]):
    log.info("Use 'netlab initial --limit netlab_no_reload' to deploy initial configuration on"+ \
             " devices that don't support configuration reload")

def run(cli_args: typing.List[str]) -> None:
  """
  Wrapper around the actual "run" function that catches user interrupts
  """
  try:
    run_config(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab config')
  return
