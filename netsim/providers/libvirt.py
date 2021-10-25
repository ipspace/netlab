#
# Vagrant/libvirt provider module
#

import subprocess
import re
from box import Box

from .. import common
from . import _Provider

class Libvirt(_Provider):

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def start_lab(self, topology: Box) -> None:
    common.print_verbose('libvirt lab has started, fixing Linux bridges')
    for l in topology.links:
      brname = l.get('bridge',None)
      if not brname:
        continue
      try:
        result = subprocess.run(['virsh','net-info',brname],capture_output=True,check=True,text=True)
      except:
        common.error('Cannot run net-info for libvirt network %s' % brname, module='libvirt')
        continue

      match = None
      if result and result.returncode == 0:
        match = re.search("Bridge:\\s+(.*)$",result.stdout,flags=re.MULTILINE)

      if match:
        common.print_verbose("... network %s maps into %s" % (brname,match.group(1)))
        subprocess.run(['sudo','sh','-c','echo 0x4000 >/sys/class/net/%s/bridge/group_fwd_mask' % match.group(1)],check=True)
        common.print_verbose("... setting LLDP enabled flag on %s" % (match.group(1)))
      else:
        common.error('Cannot get Linux bridge name for libvirt network %s' % brname, module='libvirt')
