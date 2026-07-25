#
# Arrcus ArcOS quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


class ARCOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module', [])

    # Static VXLAN flooding and the EVPN control plane are mutually exclusive on ArcOS: the global
    # 'overlay static-vxlan' knob switches the whole box into flood-and-learn mode, and the device
    # then refuses the EVPN configuration templates/evpn/arcos.j2 emits --
    #   Aborted: 'overlay static-vxlan' (value "true"): 'network-instance advertise-mac-routes'
    #            must not be true when 'overlay static-vxlan' is true
    # netlab core allows the combination (an EVPN node keeps 'static' among vxlan.flooding's valid
    # values), so without this check the topology transforms and deploys and only dies partway
    # through 'netlab initial' with a raw vendor error. Refuse it up front instead: rendering the
    # EVPN half and silently dropping the static request -- or the reverse -- would leave the user
    # with a device configured differently from the topology they wrote.
    #
    # Gated on the vxlan module as well: an EVPN node without it (a pure EVPN route reflector, or
    # an EVPN/MPLS PE) has no VTEP and no flooding mode, so there is nothing to conflict with.
    if 'evpn' in mods and 'vxlan' in mods and node.get('vxlan', {}).get('flooding', 'static') != 'evpn':
      report_quirk(
        text=f'ArcOS cannot combine EVPN with static VXLAN flooding (node {node.name})',
        more_hints=[
          'ArcOS "overlay static-vxlan" is a global flood-and-learn mode that the device refuses '
          'to run together with the EVPN control plane',
          f'Use vxlan.flooding: evpn on node {node.name}, or remove the evpn module from it' ],
        node=node,
        quirk='evpn_static_flooding',
        category=log.IncorrectValue)
