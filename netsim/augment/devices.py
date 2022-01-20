"""
Device utility functions
"""

import typing

from box import Box

from .. import common

def get_device_data(node: Box, attr: str, defaults: Box) -> typing.Optional[typing.Any]:
  devtype  = node.device
  provider = defaults.provider

  if not devtype in defaults.devices:
    common.fatal(f'Internal error: call to get_device_data with unknown device {devtype}')
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

def get_provider_data(node: Box, defaults: Box) -> Box:
  devtype  = node.device
  provider = defaults.provider

  if not devtype in defaults.devices:
    common.fatal(f'Internal error: call to get_provider_data with unknown device {devtype}')

  return defaults.devices[devtype].get(provider,Box({}))

def get_provider(node: Box, defaults: Box) -> str:
  return defaults.provider

def augment_device_settings(topology: Box) -> None:
  plist = list(topology.defaults.providers.keys())

  # Copy provider.image settings into image.provider dictionary
  for devdata in topology.defaults.devices.values():
    for p in plist:
      if p in devdata and 'image' in devdata[p]:
        devdata.image[p] = devdata[p].image
