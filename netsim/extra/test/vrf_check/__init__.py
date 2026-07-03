#
# Check whether the device under test supports VRFs and removes
# VRF links and related tests if needed
#

from box import Box

from netsim.augment.devices import get_device_features
from netsim.utils import log


def remove_vrf(ndata: Box, topology: Box) -> None:
  if 'vrf' in topology.module:
    log.info(f'Removing vrf from topology modules')
    topology.module.remove('vrf')
  if 'vrf' in ndata:
    log.info(f'Removing vrf from node {ndata.name} modules')
    ndata.module.remove('vrf')
  if 'vrfs' in topology:
    log.info(f'Removing vrfs from lab topology')
    topology.pop('vrfs',None)
  if 'vrfs' in ndata:
    log.info(f'Removing vrfs from node data')
    ndata.pop('vrfs',None)

  if 'routing.static' in ndata:
    ndata.routing.static = [ sr for sr in ndata.routing.static if 'vrf' not in sr ]

  for link in topology.links:
    if 'vrf' in link:
      log.info(f'Removing vrf from link {link._linkname}')
      link.pop('vrf',None)

    for intf in link.interfaces:
      if 'vrf' in intf:
        log.info(f'Removing vrf from interface {link._linkname}/{intf.node}')
        intf.pop('vrf',None)

  if 'validate' in topology:
    for test in list(topology.validate.keys()):
      if 'vrf' in test:
        log.info(f'Removing validation test {test}')
        topology.validate.pop(test,None)
    topology.validate.v_warning = {
      'wait': 0,
      'level': 'warning',
      'fail': f'Device {ndata.device} does support VRFs, skipping VRF-specific tests' }

def pre_transform(topology: Box) -> None:
  for node,ndata in topology.nodes.items():
    if 'vrf' not in ndata.get('module',[]):
      continue

    features = get_device_features(ndata,topology.defaults)
    if features.get('vrf',None):
      continue

    log.warning(
      text=f'Device {ndata.device}/{node} does not support VRFs',
      module='vrf_check')
    remove_vrf(ndata,topology)
