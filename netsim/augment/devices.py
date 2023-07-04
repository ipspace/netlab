"""
Device utility functions
"""

import typing

from box import Box

from .. import common
from .. import data

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
    common.fatal(f'Internal error: call to get_device_attribute with unknown device {devtype}')
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
    common.fatal('Device features for device type {node.device} should be a dictionary')
    return data.get_empty_box()

  return features

"""
Get all device data for current provider
"""
def get_provider_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = get_provider(node,defaults)

  if not devtype in defaults.devices:
    common.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

  return defaults.devices[devtype].get(provider,{})

"""
Get consolidated device data
"""
def get_consolidated_device_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = get_provider(node,defaults)

  if not devtype in defaults.devices:
    common.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

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

  for dname in list(devs.keys()):                           # Iterate over all known devices
    ddata = devs[dname]
    if not 'features' in ddata:                             # Skip devices without features
      continue

    for m in list(ddata.features.keys()):                   # Iterate over device features
      if not m in sets:
        continue                                            # Weird feature name, skip it

      mdata = sets[m]                                       # Get module data
      if not 'attributes' in mdata:                         # Is this a valid module?
        continue                                            # ... not without attributes

      if not 'supported_on' in mdata:                       # Create 'supported_on' list if needed
        mdata.supported_on = []

      if ddata.feature[m] is False and dname in mdata.supported_on:       
        mdata.supported_on.remove(dname)                    # The device DOES NOT support the module
        ddata.features.pop(m)                               # Remove the feature so it won't crash the transformation
        continue

      if not dname in mdata.supported_on:                   # Append device to module support list if needed
        mdata.supported_on.append(dname)

      f_value = ddata.features[m]
      if f_value is None or f_value is True:                # Normalize features to dicts
        ddata.features[m] = {}

"""
Initial device setting augmentation:

* Build supported_on module lists
* Future: Inherit device data from parent devices
"""
def augment_device_settings(topology: Box) -> None:
  process_device_inheritance(topology)
  build_module_support_lists(topology)
