#
# Create Ansible inventory
#
import typing

import yaml
import os
import sys
from box import Box

from .. import common
from . import _TopologyOutput
from .common import adjust_inventory_host

def create(nodes: typing.List[Box], defaults: Box, addressing: typing.Optional[Box] = None) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  if addressing:
    inventory.all.vars.pools = addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  for node in nodes:
    inventory[node.name] = adjust_inventory_host(
                             node = node,
                             defaults = defaults,
                             ignore = ['name'],
                             group_vars = True)

  return inventory

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    if callable(getattr(data,"to_yaml",None)):
      output.write(data.to_yaml())
    else:                            # pragma: no cover -- this should never happen as we're using Box, but just in case...
      output.write(yaml.dump(data))
    output.close()

min_inventory_data = [ 'id','ansible_host','ansible_port' ]

def write_devices(data: Box, fname: str, fmt: typing.Optional[str]) -> None:
  fmt = fmt or 'standard'
  addressing = data.get('addressing',{}) if 'pools' in fmt else None

  inventory = create(data['nodes'],data.get('defaults',{}),addressing)

  header = "# Netsim Devices inventory created from %s\n#\n---\n" % data.get('input','<unknown>')

  write_yaml(inventory,fname,header)
  print("Created Netsim Devices inventory %s" % fname)

def read_inventory(host: str, filename: typing.Optional[str] = None) -> typing.Optional[dict]:
  filename = filename or os.getenv('NETSIM_DEVICES') or 'netsim-devices.yml'
  if not os.path.isfile(filename):
    common.fatal('Cannot read netsim device inventory: %s does not exist')
    return None
  try:
    data = Box().from_yaml(filename=filename,default_box=True,box_dots=True,default_box_none_transform=False)
  except:
    common.fatal("Cannot read YAML from %s: %s " % (filename,str(sys.exc_info()[1])))

  if host in (data or {}):
    return data[host]

  return None

class DeviceInventory(_TopologyOutput):

  def write(self, topology: Box) -> None:
    hostfile = self.settings.hostfile or 'netsim-devices.yml'
    output_format = None

    if hasattr(self,'filenames'):
      hostfile = self.filenames[0]
      if len(self.filenames) > 1:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),common.IncorrectValue,'devices')

    if self.format:
      output_format = self.format[0]

    write_devices(topology,hostfile,output_format)
