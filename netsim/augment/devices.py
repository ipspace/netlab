"""
Device utility functions
"""

import typing
from enum import Enum

from box import Box

from .. import data
from ..utils import log, strings

"""
Get generic device attribute:

* Use node.device to find device used by the current node
* Use defaults.provider (future: node data) to find the provider
* Fetch required data using the following inheritance rules:

  * If the provider data is not a dictionary, return that (no merge)
  * If the provider data is a dictionary, but the device data is not, return provider data (override)
  * Return a merge of both dictionaries
"""
def get_device_attribute(node: Box, attr: str, defaults: Box) -> typing.Optional[typing.Any]:
  devtype  = node.device
  provider = get_provider(node,defaults)

  if not devtype in defaults.devices:    # pragma: no cover
    log.fatal(f'Internal error: call to get_device_attribute with unknown device {devtype}')
    return None

  pvalue = None
  devdata = defaults.devices[devtype]

  if provider in devdata:                # Does this device have attributes for current provider?
    if attr in devdata[provider]:        # Including the attribute we're looking for?
      pvalue = devdata[provider][attr]   # Get the provider value
      if not isinstance(pvalue,dict):    # Provider-specific value is not a dictionary
        return pvalue                    # No chance of merging, return it

  value = devdata.get(attr,None)         # Non-specific device data
  if isinstance(value,Box) and isinstance(pvalue,Box):
    return value+pvalue                  # Return merged dictionaries

  if attr in devdata[provider]:          # Do we have a provider-specific value?
    return pvalue                        # Provider-specific dictionary overriding non-dictionary device value

  return value                           # Return whatever the device value is

"""
Get device feature flags -- uses get_device_attribute but returns a Box to keep mypy happy
"""
def get_device_features(node: Box, defaults: Box) -> Box:
  n_features = node.get('_features',{})
  if not isinstance(n_features,Box):
    n_features = data.get_empty_box()

  features = get_device_attribute(node,'features',defaults)
  if not features:
    return n_features

  if not isinstance(features,Box):
    log.fatal('Device features for device type {node.device} should be a dictionary')
    return data.get_empty_box()

  return features + n_features

"""
Check whether the 'data' used in 'node' at 'path' contains valid optional device features

The checking algorithm is specified with the check_mode parameter:

* WHITELIST requires that every element used in 'data' is a feature
* BLACKLIST reports errors for elements in features. The value of those features could
  be 'False' (not supported) or a string (error message)
"""
class FC_MODE(Enum):
  BLACKLIST    = 1
  WHITELIST    = 2
  OK           = 1
  ERR_ATTR     = -2
  ERR_OPTIONAL = -1

def optional_features_error(
      node: Box,
      attribute: str,
      path: str,
      module: str,
      category: typing.Optional[typing.Union[typing.Type[Warning],typing.Type[Exception]]] = None) -> None:

  log.error(
    f'Device {node.device} does not support {attribute} used in {path}',
    category=log.IncorrectAttr if category is None else category,
    module=module)

def check_optional_features(
        data: Box,                  # The lab topology data to check
        path: str,                  # Path used in error messages
        node: Box,                  # Parent node data
        topology: Box,              # Topology data (needed to fetch device features)
        attribute: str,             # Path to the feature to check
        check_mode: FC_MODE = FC_MODE.WHITELIST,
        category: typing.Optional[typing.Union[typing.Type[Warning],typing.Type[Exception]]] = None,
        features: typing.Optional[Box] = None) -> FC_MODE:

  module = attribute.split('.')[0]
  if features is None:              # Fetch the initial device features (we'll set the value in recursive calls)
    d_features = get_device_features(node,topology.defaults)
    features = d_features.get(attribute,False)

  if features is True:              # We got to a TRUE value, this stuff is supported
    return FC_MODE.OK

  if features is False:             # The device has no idea about the required feature, get out of here
    optional_features_error(node,attribute,path,module,category)
    return FC_MODE.ERR_OPTIONAL if category is Warning else FC_MODE.ERR_ATTR

  if isinstance(features,str):      # Custom error message
    log.error(
      features,
      category=Warning if category is None else category,
      more_data=f'Used in {path}',
      module=module)
    return FC_MODE.ERR_OPTIONAL if category is None or category is Warning else FC_MODE.ERR_ATTR

  if isinstance(data,Box) and isinstance(features,Box):
    OK = FC_MODE.OK
    for kw in data.keys():          # Check all subfeatures
      if kw in features:            # Subfeature is mentioned, do a recursive check
        stat = check_optional_features(
                  data[kw],f'{path}.{kw}',node,topology,
                  f'{attribute}.{kw}',check_mode,category,features[kw])
        if stat.value < OK.value:
          OK = stat
        continue                    # ... and move to the next feature
      if check_mode == FC_MODE.BLACKLIST:
        continue                    # Subfeature is not mentioned, we're in blacklist mode == > OK
      optional_features_error(node,f'{attribute}.{kw}',f'{path}.{kw}',module,category)
      OK = FC_MODE.ERR_ATTR         # In whitelisting mode a missing subfeature is an error

    return OK                       # Return the final result
  else:                             # Assume the feature is supported
    return FC_MODE.OK

"""
Get device loopback name (built-in loopback if ifindex == 0 else an additional loopback)
"""
def get_loopback_name(node: Box, topology: Box, ifindex: int = 0) -> typing.Optional[str]:
  lbname = get_device_attribute(node,'loopback_interface_name',topology.defaults)
  if not lbname:
    return None
  
  return strings.eval_format(lbname,{ 'ifindex': ifindex })

"""
Get all device data for current provider
"""
def get_provider_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = get_provider(node,defaults)

  if not devtype in defaults.devices:
    log.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

  return defaults.devices[devtype].get(provider,{})

"""
Get consolidated device data
"""
def get_consolidated_device_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = get_provider(node,defaults)

  if not devtype in defaults.devices:
    log.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

  data = defaults.devices[devtype] + defaults.devices[devtype].get(provider,{})
  for p in defaults.providers.keys():
    data.pop(p,None)

  return data

"""
Get node provider -- currently returns the default provider, but we'll do fun stuff pretty soon ;)
"""
def get_provider(node: Box, defaults: Box) -> str:
  return node.get('provider',defaults.provider)

"""
process_device_inheritance: for devices with 'parent' attribute merge parent settings with the
device settings.

The main work is done in the process_child_device function that is called recursively to process
multi-level inheritance. Please note that the circular references are broken at a random place
in the ring because the 'parent' attribute is removed before the recursive call
"""
def process_child_device(dname: str, devices: Box) -> None:
  if not 'parent' in devices[dname]:                        # This device is not a child device, nothing to do
    return
  
  p_device = devices[dname].parent                          # Remember the parent device
  devices[dname].pop('parent',None)                         # ... and remove it to break potential circular references

  process_child_device(p_device,devices)                    # Process inheritance in parent device
  p_data = Box(devices[p_device].to_dict())                 # Build a copy of parent device data
  for kw in ("template","_meta_device"):                    # ... remove the template/meta device flags
    p_data.pop(kw,None)
  devices[dname] = p_data + devices[dname]                  # ... and merge parent settings with the child device
  data.append_to_list(devices[dname],'_parents',p_device)

  data.remove_null_values(devices[dname])                   # Finally, remove null values from the resulting dictionary

def process_device_inheritance(topology: Box) -> None:
  devices = topology.defaults.devices
  for dname in list(devices.keys()):
    process_child_device(dname,devices)

"""
Add device features (optionally provider-limited) to module support list
"""
def add_device_module_support(
      topology: Box,
      features: Box,
      dname: str,
      provider: typing.Optional[str] = None) -> None:
  sets = topology.defaults
  for m in list(features.keys()):                   # Iterate over device features
    f_value = features[m]
    if f_value is None or f_value is True:          # Normalize features to dicts
      features[m] = {}

    if not m in sets:
      continue                                      # Weird feature name, skip it

    mdata = sets[m]                                 # Get module data
    if not isinstance(mdata,Box):                   # Hope it's a box or something is badly messed up
      log.fatal(f'Internal error: definition of module {mdata} is not a dictionary')

    if not 'attributes' in mdata:                   # Is this a valid module?
      continue                                      # ... not without attributes

    if f_value is False:                            # Device definitely DOES NOT support the feature
      features.pop(m)                               # Remove the feature so it won't crash the transformation
      continue                                      # ... and skip it

    if not dname in mdata.supported_on:             # Append device to module support list if needed
      if provider:
        mdata.supported_on[dname][provider] = True
      else:
        mdata.supported_on[dname] = True

    if provider:
      features[m]._provider = provider              # Remember we're dealing with provider-specific features

"""
Build module supported_on lists based on device features settings
"""
def build_module_support_lists(topology: Box) -> None:
  sets = topology.defaults
  devs = sets.devices

  for dname in sorted(list(devs.keys())):                   # Iterate over all known devices
    ddata = devs[dname]
    if not 'features' in ddata:                             # Skip devices without features
      continue

    add_device_module_support(topology,ddata.features,dname,None)

    for p_name in sets.providers.keys():                    # Finally, iterate over providers
      if p_name in ddata and 'features' in ddata[p_name]:   # Do we have provider-specific features?
        add_device_module_support(topology,ddata[p_name].features,dname,p_name)

"""
Merge daemons definitions into device definitions
"""
def merge_daemons(topology: Box) -> None:
  if not 'daemons' in topology.defaults:
    return

  daemons = topology.defaults.daemons
  devices = topology.defaults.devices

  for dname in daemons.keys():                              # To be on the safe side...
    if not isinstance(daemons[dname],Box):                  # ... validate daemon definition data type
      log.fatal(f'Internal error: definition of daemon {dname} is not a dictionary')
    if dname in devices:                                    # ... and check for duplicate names
      log.fatal(f'Internal error: duplicate name {dname} for a device and a daemon')

  for dname in list(daemons):
    devices[dname] = daemons[dname]
    devices[dname].daemon = True                            # Mark the device as a daemon
    if 'netlab_device_type' not in devices[dname].group_vars:
      devices[dname].group_vars.netlab_device_type = dname  # Remember the device type (needed for config templates)
    if not 'parent' in devices[dname]:
      devices[dname].parent = 'linux'                       # Most daemons run on Linux

    devices[dname].daemon_parent = devices[dname].parent    # Save the parent for future use (it is removed when merging parent device data)

"""
Add device-specific attributes
"""
def add_device_attributes(topology: Box) -> None:
  for dev_def in topology.defaults.devices.values():        # Iterate over all devices
    if 'attributes' in dev_def:                             # ... and add device specific attributes to the data model
      topology.defaults.attributes = topology.defaults.attributes + dev_def.attributes

"""
Initial device setting augmentation:

* Build supported_on module lists
* Future: Inherit device data from parent devices
"""
def augment_device_settings(topology: Box) -> None:
  devices = topology.defaults.devices

  if not isinstance(devices,Box):
    log.fatal('Internal error: defaults.devices must be a dictionary')

  for dname in devices.keys():                    # To be on the safe side...
    if not isinstance(devices[dname],Box):        # ... validate device definition data type
      log.fatal(f'Internal error: definition of device {dname} is not a dictionary')

  merge_daemons(topology)
  add_device_attributes(topology)
  process_device_inheritance(topology)
  build_module_support_lists(topology)

  for dname in list(devices.keys()):              # After completing device transformation, do a few sanity checks
    if 'template' in devices[dname]:              # Remove template devices
      devices.pop(dname,None)
      continue

    for kw in ['interface_name','description']:   # List of mandatory attributes
      if not kw in devices[dname]:
        log.error(
          f'Device {dname} defined in defaults.devices.{dname} does not have {kw} attribute',
          log.IncorrectValue,
          'devices')

  log.exit_on_error()
