#
# Vagrant/libvirt provider module
#

import subprocess
import re
from box import Box
import pathlib

from .. import common
from . import _Provider

LIBVIRT_MANAGEMENT_NETWORK_NAME = "vagrant-libvirt"
LIBVIRT_MANAGEMENT_NETWORK_FILE = "templates/provider/libvirt/vagrant-libvirt.xml"

class Libvirt(_Provider):

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def pre_start_lab(self, topology: Box) -> None:
    common.print_verbose('pre-start hook for libvirt')
    # Starting from vagrant-libvirt 0.7.0, the destroy actions deletes all the networking
    #  including the "vagrant-libvirt" management network.
    #  Let's re-create it if missing!
    try:
      result = subprocess.run(['virsh','net-info',LIBVIRT_MANAGEMENT_NETWORK_NAME],capture_output=True,text=True)
      if result.returncode == 1:
        # When ret code is 1, the network is missing
        common.print_verbose('creating missing %s network' % LIBVIRT_MANAGEMENT_NETWORK_NAME)
        net_template_xml = pathlib.Path(__file__).parent.parent.joinpath(LIBVIRT_MANAGEMENT_NETWORK_FILE).resolve()
        result2 = subprocess.run(['virsh','net-define',net_template_xml],capture_output=True,check=True,text=True)
    except subprocess.CalledProcessError as e:
      common.error('Exception in net handling for libvirt network %s: [%s] %s' % (LIBVIRT_MANAGEMENT_NETWORK_NAME, e.returncode, e.stderr), module='libvirt')
    return

  def post_start_lab(self, topology: Box) -> None:
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
