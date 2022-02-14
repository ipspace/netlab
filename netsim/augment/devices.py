"""
Device utility functions
"""

import typing

from box import Box

from .. import common

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
  provider = defaults.provider

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
    return Box({},default_box=True,box_dots=True)

  if not isinstance(features,Box):
    common.fatal('Device features for device type {node.device} should be a dictionary')
    return Box({})

  return features

"""
Get all device data for current provider
"""
def get_provider_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = defaults.provider

  if not devtype in defaults.devices:
    common.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

  return defaults.devices[devtype].get(provider,{})

"""
Get consolidated device data
"""
def get_consolidated_device_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = defaults.provider

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
  return defaults.provider

def augment_device_settings(topology: Box) -> None:
  pass
