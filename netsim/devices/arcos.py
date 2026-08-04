#
# Arrcus ArcOS quirks
#
import ipaddress

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

    # An ArcOS prefix-set is a flat member list: the accept/reject decision lives on the policy
    # statement that references it, not on the individual members. A netlab prefix list carries an
    # action per entry, and its semantics are first-match-wins, so a 'deny' entry means "this
    # prefix does NOT match the list".
    #
    # templates/routing/arcos.j2 renders the PERMIT entries only, which is faithful as long as no
    # deny entry shadows a permit entry that comes after it. When they overlap, order is the only
    # thing separating them and a flat set cannot carry order: a prefix caught by the earlier deny
    # would still match the later permit's member and be treated as matching the list. That is a
    # route-map matching the wrong routes -- silent, and visible only as traffic taking the wrong
    # path -- so refuse it rather than approximate it.
    for pfx_name, pfx_list in node.get('routing.prefix', {}).items():
      for (idx, deny) in enumerate(pfx_list):
        if deny.get('action', 'permit') != 'deny':
          continue
        for later in pfx_list[idx + 1:]:
          if later.get('action', 'permit') == 'deny':
            continue
          for af in ('ipv4', 'ipv6'):                       # Same family, and do the nets overlap?
            if af not in deny or af not in later:
              continue
            if not ipaddress.ip_network(deny[af]).overlaps(ipaddress.ip_network(later[af])):
              continue
            report_quirk(
              text=f'ArcOS cannot express prefix list {pfx_name} on node {node.name}: '
                   f'the deny entry {deny[af]} shadows the later permit entry {later[af]}',
              more_hints=[
                'An ArcOS prefix-set is a flat member list with no per-entry action and no ordering, '
                'so a deny entry can only be expressed by leaving the prefix out of the set -- which '
                'does not work when a later permit entry covers it as well',
                f'Reorder {pfx_name} so no deny entry overlaps a permit entry below it, or split it '
                'into separate lists' ],
              node=node,
              quirk='prefix_list_shape',
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
