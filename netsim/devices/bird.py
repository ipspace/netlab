#
# Bird quirks
#
from box import Box

from . import _Quirks
from ._common import check_daemon_dataplane_config
from .linux import etc_resolv_mapping


def bird_transform_rt(rt: str) -> str:
  '''
  Transform standard RT notation A:B into BIRD RT notation (rt,A,B)

  Split the original route target into its components, rejoin them
  separated by commas and add (rt,) around them
  '''
  return '(rt,'+','.join(rt.split(':'))+')'

def bird_vrf_rt(node: Box) -> None:
  '''
  Convert standard VRF route targets into (rt,a,b) format used by Bird configuration
  '''
  for vdata in node.get('vrfs',{}).values():                # Iterate over all VRFs
    for kw in ('import','export'):                          # Process import and export RTs
      if kw not in vdata:                                   # Not relevant? Cool ;)
        continue

      vdata[f'_bird_{kw}'] = [ bird_transform_rt(rt) for rt in vdata[kw]]

def bird_vlan_evpn_rt(node: Box) -> None:
  '''
  Convert standard MAC VRF EVPN route targets into (rt,a,b) format used by Bird configuration

  Note: the IP-VRF EVPN RTs are transformed by bird_vrf_rt function
  '''
  for vdata in node.get('vlans',{}).values():               # Iterate over all VLANs
    if 'evpn' not in vdata:                                 # Skip non-EVPN VLANs
      continue
    for kw in ('import','export'):                          # Process import and export RTs
      if kw not in vdata.evpn:                              # Not relevant? Cool ;)
        continue

      vdata.evpn[f'_bird_{kw}'] = [ bird_transform_rt(rt) for rt in vdata.evpn[kw]]

class Bird(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    etc_resolv_mapping(node,topology)
    check_daemon_dataplane_config(node,topology)
    bird_vrf_rt(node)
    bird_vlan_evpn_rt(node)
