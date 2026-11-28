#
# Create devices inventory in YAML format
#
import os
import typing

from box import Box

from ..utils import files as _files
from ..utils import log, strings
from . import _TopologyOutput, check_writeable
from .common import adjust_inventory_host


def create(nodes: Box, defaults: Box, addressing: typing.Optional[Box] = None) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  if addressing:
    inventory.all.vars.pools = addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  for name,node in nodes.items():
    inventory[name] = adjust_inventory_host(
                        node = node,
                        defaults = defaults,
                        ignore = ['name'],
                        group_vars = True)

  return inventory

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with _files.open_output_file(fname) as output:
    output.write(header)
    output.write(strings.get_yaml_string(data))
    output.close()

min_inventory_data = [ 'id','ansible_host','ansible_port' ]

def write_devices(data: Box, fname: str, fmt: typing.Optional[str]) -> None:
  fmt = fmt or 'standard'
  addressing = data.get('addressing',{}) if 'pools' in fmt else None

  inventory = create(data.nodes,data.get('defaults',{}),addressing)

  header = "# Netlab Devices inventory created from %s\n#\n" % data.get('input','<unknown>')

  write_yaml(inventory,fname,header)
  print("Created netlab devices inventory %s" % fname)

class DeviceInventory(_TopologyOutput):

  DESCRIPTION :str = 'Create simple device inventory as a YAML file'

  def write(self, topology: Box) -> None:
    check_writeable('netlab-devices.yml')
    hostfile = self.settings.hostfile or 'netlab-devices.yml'
    output_format = None

    if hasattr(self,'filenames'):
      hostfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,'devices')

    if self.format:
      output_format = self.format[0]

    write_devices(topology,hostfile,output_format)
