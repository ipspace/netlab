#
# Bird quirks
#
from box import Box

from . import _Quirks
from ._common import check_daemon_dataplane_config, check_indirect_static_routes


def bird_vrf_rt(node: Box) -> None:
  '''
  Convert standard route targets into (rt,a,b) format used by Bird configuration
  '''
  for vdata in node.get('vrfs',{}).values():                # Iterate over all VRFs
    for kw in ('import','export'):                          # Process import and export RTs
      if kw not in vdata:                                   # Not relevant? Cool ;)
        continue

      '''
      The magic of the following line explained for people who don't want to study it ;)

      * Iterate over all route targets in the import/export list
      * Split the original route target (asn:rt or ip:rt) into its components
      * Rejoin the RT components separated by commas (OK, I could have used replace, but this
        is way cooler :-P )
      * Add (rt,) around the RT components
      '''
      vdata[f'_bird_{kw}'] = [ '(rt,'+','.join(rt.split(':'))+')' for rt in vdata[kw]]

class Bird(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_daemon_dataplane_config(node,topology)
    bird_vrf_rt(node)
