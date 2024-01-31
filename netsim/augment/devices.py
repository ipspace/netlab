"""
Device utility functions
"""

import typing

from box import Box

from .. import data
from ..utils import log,strings

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
  features = get_device_attribute(node,'features',defaults)
  if not features:
    return data.get_empty_box()

  if not isinstance(features,Box):
    log.fatal('Device features for device type {node.device} should be a dictionary')
    return data.get_empty_box()

  return features

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
  devices[dname] = devices[p_device] + devices[dname]       # ... and merge parent settings with the child device

  data.remove_null_values(devices[dname])                   # Finally, remove null values from the resulting dictionary

def process_device_inheritance(topology: Box) -> None:
  devices = topology.defaults.devices
  for dname in list(devices.keys()):
    process_child_device(dname,devices)

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

    for m in list(ddata.features.keys()):                   # Iterate over device features
      f_value = ddata.features[m]
      if f_value is None or f_value is True:                # Normalize features to dicts
        ddata.features[m] = {}

      if not m in sets:
        continue                                            # Weird feature name, skip it

      mdata = sets[m]                                       # Get module data
      if not isinstance(mdata,Box):                         # Hope it's a box or something is badly messed up
        log.fatal(f'Internal error: definition of module {mdata} is not a dictionary')

      if not 'attributes' in mdata:                         # Is this a valid module?
        continue                                            # ... not without attributes

      if f_value is False:                                  # Device definitely DOES NOT support the feature
        ddata.features.pop(m)                               # Remove the feature so it won't crash the transformation
        continue                                            # ... and skip it

      if not 'supported_on' in mdata:                       # Create 'supported_on' list if needed
        mdata.supported_on = []

      if not dname in mdata.supported_on:                   # Append device to module support list if needed
        mdata.supported_on.append(dname)

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
Initial device setting augmentation:

* Build supported_on module lists
* Future: Inherit device data from parent devices
"""
def augment_device_settings(topology: Box) -> None:
  devices = topology.defaults.devices

  if not isinstance(devices,Box):
    log.fatal('Internal error: defaults.devices must be a dictionary')

  for dname in devices.keys():                              # To be on the safe side...
    if not isinstance(devices[dname],Box):                  # ... validate device definition data type
      log.fatal(f'Internal error: definition of device {dname} is not a dictionary')

  merge_daemons(topology)
  process_device_inheritance(topology)
  build_module_support_lists(topology)

  for dname in devices.keys():                              # After completing device transformation, do a few sanity checks
    for kw in ['interface_name','description']:             # ... list of attributes taken from nodes
      if not kw in devices[dname]:
        log.error(
          f'Device {dname} defined in defaults.devices.{dname} does not have {kw} attribute',
          log.IncorrectValue,
          'devices')

  log.exit_on_error()
