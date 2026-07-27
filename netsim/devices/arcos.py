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
    if 'evpn' in mods and 'vxlan' in mods and node.get('vxlan.flooding', 'static') != 'evpn':
      report_quirk(
        text=f'ArcOS cannot combine EVPN with static VXLAN flooding (node {node.name})',
        more_hints=[
          'ArcOS "overlay static-vxlan" is a global flood-and-learn mode that the device refuses '
          'to run together with the EVPN control plane',
          f'Use vxlan.flooding: evpn on node {node.name}, or remove the evpn module from it' ],
        node=node,
        quirk='evpn_static_flooding',
        category=log.IncorrectValue)

    # ArcOS can only turn spanning tree off for the WHOLE box: the off switch is the global
    # "stp enabled-protocol NONE". "stp rapid-pvst vlan <id>" has no 'enabled' leaf, and neither
    # does "stp interface <if>" -- there is nowhere to put a per-VLAN disable request.
    #
    # netlab core gates the per-interface form (intf.stp.enable) against features.stp.enable_per_port,
    # which ArcOS declares False, so that one is already refused. It does NOT gate the per-VLAN form
    # against anything, so vlans.<name>.stp.enable: False transforms, renders and deploys -- and
    # templates/stp/arcos.j2 has nothing to render for it, leaving spanning tree RUNNING on a VLAN
    # the topology says it should be off on. That is a wrong topology rather than an error, and on
    # a node that also carries stp.priority the rendered config makes the device the root bridge of
    # exactly the VLAN the user asked to exclude. Refuse the combination up front instead.
    if 'stp' in mods:
      no_stp_vlans = [
          vname for vname, vdata in node.get('vlans', {}).items()
            if vdata.get('stp.enable', True) is False ]
      if no_stp_vlans:
        report_quirk(
          text=f'ArcOS cannot disable STP on individual VLANs (node {node.name}, '
               f'VLAN(s) {",".join(no_stp_vlans)})',
          more_hints=[
            'ArcOS has no per-VLAN "enabled" leaf -- the only off switch is the global '
            '"stp enabled-protocol NONE", which stops spanning tree on the whole device',
            f'Use stp.enable: False on node {node.name} to stop STP everywhere, or remove the '
            'per-VLAN stp.enable setting' ],
          node=node,
          quirk='stp_vlan_disable',
          category=log.IncorrectValue)
