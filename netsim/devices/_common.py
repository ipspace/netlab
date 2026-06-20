#
# Common quirks that can be used by more than one device
#
from box import Box

from ..augment import devices as a_devices
from ..utils import log
from . import report_quirk


def check_indirect_static_routes(node: Box) -> None:
  for sr_entry in node.get('routing.static',[]):
    if 'discard' in sr_entry.nexthop:
      continue
    if 'intf' not in sr_entry.nexthop:
      report_quirk(
        f'static routes with indirect next hops cannot be used (node {node.name})',
        node=node,
        quirk='indirect_nexthop',
        more_data=f'Static route data: {sr_entry}')

def requires_plugin(node: Box, plugin: str, topology: Box) -> None:
  if plugin not in topology.get('plugin',[]):
    log.error(
      f'Device {node.device} (node {node.name}) requires "{plugin}" plugin to work properly',
      more_hints=f'Add "{plugin}" to the topology "plugin" list',
      category=log.MissingDependency,
      module=node.device)

def check_daemon_dataplane_config(node: Box, topology: Box) -> None:
  """
  Checks whether a daemon uses a module that requires additional dataplane configuration

  If such a module is found, the function puts plumbing in place to ensure the control-plane
  daemon is started only when the dataplane configuration is finished. It is assumed that
  the '/etc/dataplane-wait.sh' script is available on the device.
  """
  features = a_devices.get_device_features(node,topology.defaults)    # Get device features
  dp_config = features.initial.get('dataplane_config',[])             # Do we have to take care of dataplane configs?
  dp_module = [ m for m in node.get('module',[]) if m in dp_config ]  # Does this node use any of those modules?
  if not dp_module:                                                   # Nope? Cool, we're done
    return

  node.netlab_dp_module = dp_module                                   # Remember the modules (we'll need them later)
  n_clab = node.clab                                                  # We also need to change clab data
  n_clab.cmd = '/etc/dataplane-wait.sh'                               # Entry point is now the "wait for dataplane config" script
  n_clab.config_templates['dataplane-wait'] = '/etc/dataplane-wait.sh:sh'
  report_quirk(
    f"Control-plane daemon on node {node.name} will have to wait for {','.join(dp_module)} data-plane configuration",
    node=node,
    quirk='dataplane_config',
    info=True)
