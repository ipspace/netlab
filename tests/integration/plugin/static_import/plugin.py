"""
Check whether the device under test supports static routing and import of static
routes into the routing protocol(s) configured on the device.

If the device under test (the node using 'routing' module) does not support
these features:

* Removes 'routing' module and 'routing' attribute from the node
* Removes 'static' from routing protocol imports
* Adds a warning to the validation tests
"""

import typing
from box import Box
from netsim.augment.devices import get_device_features
from netsim.utils import log
from netsim.data import get_box

def remove_validation(topology: Box, warning: str) -> None:
  for tname,tdata in get_box(topology.validate).items():
    if 'static' in tname:
      log.info(f'Removing validation test {tname}')
      topology.validate.pop(tname,None)

  topology.validate.r_warning = {
    'wait': 0,
    'level': 'warning',
    'fail': warning }

def is_static_import(attr: typing.Any) -> bool:
  if not isinstance(attr,Box):                        # Current node attribute is not a box, move on
    return False
  if 'import' not in attr:                            # ... or it does not have 'import' key
    return False
  if not isinstance(attr['import'],Box):              # ... or the 'import' key is not a dictionary
    return False
  
  return 'static' in attr['import']                   # ... We have imports, check whether we're importing static

def remove_routing(ndata: Box, topology: Box, warning: str) -> None:
  if 'routing' in ndata:
    log.info(f'Removing routing from node {ndata.name} modules')
    ndata.module.remove('routing')
    ndata.pop('routing',None)

  for n_attr,n_data in ndata.items():                 # Now remove all mentions of static route imports
    if not is_static_import(n_data):
      continue
    n_data['import'].pop('static',None)
    log.info(f'Removing import of static routes from {n_attr}')

  remove_validation(topology,warning)

def check_static_import(ndata: Box, features: Box, topology: Box) -> None:
  for n_attr,n_data in ndata.items():                 # Check for static route imports
    if not is_static_import(n_data):
      continue
    if 'static' in features[n_attr]['import']:
      continue
    msg = f'Device {ndata.device}/{ndata.name} does not support import of static routes into {n_attr}'
    n_data['import'].pop('static',None)
    log.warning(
      text=msg,
      module='routing_check')

    remove_validation(topology,msg)

def pre_transform(topology: Box) -> None:
  for node,ndata in topology.nodes.items():
    if 'routing' not in ndata.get('module',[]):
      continue

    features = get_device_features(ndata,topology.defaults)
    if not features.get('routing.static',None):
      msg = f'Device {ndata.device}/{node} does not support static routes'
      log.warning(
        text=msg,
        module='routing_check')
      remove_routing(ndata,topology,msg)
    else:
      check_static_import(ndata,features,topology)
