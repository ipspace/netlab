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

    # An ArcOS community-set has no per-member action -- it carries a single match option for the
    # whole set (ANY / ALL / INVERT). A netlab community list has an action per entry, so only two
    # shapes have a faithful rendering (templates/routing/arcos.j2):
    #
    #   * every entry permits                     -> the members are the set,  match-set-options ANY
    #   * deny entries plus a catch-all '.*' permit -> the denied members are the set, and the sense
    #                                                is flipped with match-set-options INVERT
    #
    # Anything else -- a permit and a deny of different values in one list, or deny entries with no
    # catch-all -- would have to be approximated, and an approximated route-map match is the kind of
    # thing nobody notices until traffic goes the wrong way. Refuse it instead.
    if node.get('routing.community', None):
      for cl_name, cl_data in node.routing.community.items():
        entries = cl_data.get('value', [])
        deny = [e for e in entries if e.get('action', 'permit') == 'deny']
        if not deny:                                            # All-permit list: ANY, always fine
          continue
        other = [e for e in entries if e.get('action', 'permit') != 'deny']
        # The deny form is expressible only as "matches none of these", i.e. every non-deny entry
        # has to be the catch-all that makes the rest of the list a pure negation.
        if other and all(e.get('_value', '') == '.*' for e in other):
          continue
        report_quirk(
          text=f'ArcOS cannot express BGP community list {cl_name} on node {node.name}',
          more_hints=[
            'An ArcOS community-set has one match option for the whole set (ANY/ALL/INVERT) and no '
            'per-member action, so it can express "matches any of these" or "matches none of these" '
            'and nothing in between',
            f'Rewrite {cl_name} as a list of permit entries, or as deny entries followed by a '
            'catch-all permit' ],
          node=node,
          quirk='community_list_shape',
          category=log.IncorrectValue)
