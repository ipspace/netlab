#
# Check whether the device under test supports VRFs and removes
# VRF links and related tests if needed
#

from box import Box
from netsim.augment.devices import get_device_features

def remove_vrf(ndata: Box, topology: Box) -> None:
  if 'vrf' in topology.module:
    print(f'Removing vrf from topology modules')
    topology.module.remove('vrf')
  if 'vrf' in ndata:
    print(f'Removing vrf from node {ndata.name} modules')
    ndata.module.remove('vrf')
  if 'vrfs' in topology:
    print(f'Removing vrfs from lab topology')
    topology.pop('vrfs',None)
  if 'vrfs' in ndata:
    print(f'Removing vrfs from node data')
    ndata.pop('vrfs',None)

  for link in topology.links:
    if 'vrf' in link:
      print(f'Removing vrf from link {link._linkname}')
      link.pop('vrf',None)

    for intf in link.interfaces:
      if 'vrf' in intf:
        print(f'Removing vrf from interface {link._linkname}/{intf.node}')
        intf.pop('vrf',None)

  for test in list(topology.validate.keys()):
    if 'vrf' in test:
      print(f'Removing validation test {test}')
      topology.validate.pop(test,None)

def pre_transform(topology: Box) -> None:
  for node,ndata in topology.nodes.items():
    if 'dut' not in node:
      continue

    features = get_device_features(ndata,topology.defaults)
    if features.get('vrf',None):
      continue

    print(f'Tested device {ndata.device}/{node} does not support VRFs')
    remove_vrf(ndata,topology)
