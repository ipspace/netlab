#
# netlab initial -- implement standard device readiness checks
#
import argparse
import typing

from box import Box

from .... import providers
from ....augment import devices as a_devices
from ....data import append_to_list, get_empty_box
from ....utils import log
from ... import ansible, is_dry_run, lab_status_change
from ..utils import get_deploy_nodeset, min_ansible_args
from . import command as r_command
from . import ssh as r_ssh


def provider_health_check(waitset: list, topology: Box) -> None:
  d_provider = topology.provider
  p_set = { topology.nodes[n_name].get('provider',d_provider) for n_name in waitset }
  for provider in p_set:
    p_module = providers.get_provider_module(topology,provider)
    p_module.call('health_check',waitset,topology)

READY_ACTIONS = {
  'health': provider_health_check,
  'ssh': r_ssh.device_ssh_ready,
  'command': r_command.device_command_ready,
    }

"""
Execute all "wait for device to be ready" steps recognized by "netlab initial". Further
steps might have to be executed by Ansible playbooks
"""
def internal_device_ready(waitlists: Box, topology: Box) -> Box:
  global READY_ACTIONS

  # Iterate over known steps, check whether any device needs that, and execute
  # the corresponding ready function
  for r_step in READY_ACTIONS.keys():
    if r_step not in waitlists:                   # Nobody asked for this step, move on
      continue
    if topology.defaults.netlab.initial.ready[r_step] != 'internal':
      continue                                    # We're not using the internal code for this step

    if is_dry_run():
      log.info(f'Would execute internal {r_step} readiness check',module='dry_run')
      waitlists.pop(r_step)
      continue

    READY_ACTIONS[r_step](waitlists[r_step],topology)
    waitlists.pop(r_step)

  return waitlists

def get_waitlists(nodeset: list, topology: Box) -> Box:
  waitlists = get_empty_box()
  defaults = topology.defaults

  # Build lists of device requiring a specific ready step
  #
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    ready_steps = a_devices.get_node_group_var(n_data,'netlab_ready',defaults)
    if not isinstance(ready_steps,list):
      continue
    for step in ready_steps:
      append_to_list(waitlists,step,n_name)

  return waitlists

def run(
      topology: Box,
      args: argparse.Namespace,
      rest: typing.Optional[list] = None,
      nodeset: typing.Optional[list] = None) -> None:

  if nodeset is None:
    nodeset = get_deploy_nodeset(args,topology)
  if rest is None:
    rest = []

  node_waits = get_waitlists(nodeset,topology)
  if node_waits and not log.QUIET:
    log.section_header('Checking',f'Are lab devices ready to be configured?')

  ansible_waits = internal_device_ready(node_waits,topology)
  if ansible_waits:
    log.info(text='Checking lab devices with an Ansible playbook')
    ansible.check_version()
    ansible_limit = ['--tag',','.join(['ready_'+wl for wl in ansible_waits.keys()])]
    ansible.playbook('device-ready.ansible',rest + min_ansible_args(args) + ansible_limit)

  if args.ready:
    lab_status_change(topology,'devices are ready')
    log.info(text='Lab devices are ready to be configured')
