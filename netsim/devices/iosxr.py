#
# Cisco IOS-XR quirks
#
import typing

from box import Box

from ..data import get_new_box
from ..utils import log
from . import _Quirks, report_quirk

"""
Split prefix lists into permit_ and deny_ sets and adjust the routing policies accordingly
"""
def rp_set(node: Box, o_name: str, o_value: typing.Optional[str]) -> None:

  #
  # Get action set from a routing policy object
  #
  def rp_get_action_set(rpo_value: list) -> set:
    action_set = set()                                # Collect permit/deny actions
    oo_warning = False                                # Remember whether we emitted out-of-order warning
    for entry in rpo_value:                           # ... by iterating through the routing object entries
      action = entry.action
      action_set.add(action)                          # Remember current action
      
      # Deny-after-permit does not work, create a warning
      if action == 'deny' and 'permit' in action_set and not oo_warning:
        report_quirk(
          f'{o_name} sets with mixed permit/deny actions cannot be implemented',
          more_data=[f'Node {node.name} {o_name} set {rpo_name}'],
          more_hints=['All "deny" conditions must be before "permit" conditions'],
          quirk=f'routing_{o_name}_mixed',
          category=Warning,
          node=node)
        oo_warning = True

    return action_set

  #
  # Create permit/deny objects from the original routing policy object
  #
  def rp_create_permit_deny_objects(rpo_name: str) -> None:
    for action in ('deny','permit'):
      o_act_name = f'{rpo_name}_{action}'             # Create permit- and deny objects
      o_act_list = [ entry for entry in rpo_value if entry.action == action ]
      if o_value:                                     # Do we have to replace an attribute?
        o_act_value = get_new_box(node.routing[o_name][rpo_name])
        o_act_value[o_value] = o_act_list             # Copy the original object and replace the list value
        node.routing[o_name][o_act_name] = o_act_value
      else:
        node.routing[o_name][o_act_name] = o_act_list # Otherwise the trimmed list is the value

  #
  # Update routing policies to use the new permit/deny objects
  #
  def rp_update_routing_policies(rpo_name: str) -> None:
    for rp_value in node.routing.get('policy',{}).values():
      for rp_entry in rp_value:                       # Iterate over RP entries
        if rp_match not in rp_entry:                  # Are we matching on current object type?
          continue
        if not isinstance(rp_entry[rp_match],dict):   # Are we dealing with a simple match (prefix, as-path...)?
          if rp_entry[rp_match] != rpo_name:          # ... that is using the current object?
            continue
          for kw in ('deny','permit'):                # Create an extra attribute with permit/deny names
            rp_entry.match[f'_xr_{o_name}'][kw] = f'{rpo_name}_{kw}'
          rp_entry.pop(rp_match)                      # And remove the original attribute
        else:                                         # Community matching has an extra level of dicts
          for sub_kw in list(rp_entry[rp_match]):     # ... so we have to iterate over those as well
            sub_kval = rp_entry[rp_match][sub_kw]
            if sub_kval != rpo_name:                  # Not using the current object?
              continue
            for kw in ('deny','permit'):              # There must be a better way than duplicating the code
              rp_entry.match[f'_xr_{o_name}'][sub_kw][kw] = f'{rpo_name}_{kw}'
            rp_entry[rp_match].pop(sub_kw)            # ... I just haven't found it yet ;)
            if not rp_entry[rp_match]:                # We also need to do a potential parent cleanup when
              rp_entry.pop(rp_match)                  # ... dealing with sub-dictionaries

  # And now we're back to the regular programming ;)
  #
  if o_name not in node.routing:                      # Routing policy object not used, nothing to do
    return

  rp_match = f'match.{o_name}'                        # This is how we're matching the object in routing policies
  for rpo_name in list(node.routing[o_name].keys()):  # Iterate over routing objects
    rpo_value = node.routing[o_name][rpo_name]        # Get the list value from the object
    if o_value:                                       # ... or one of its attributes
      rpo_value = rpo_value[o_value]

    action_set = rp_get_action_set(rpo_value)
    if len(action_set) <= 1 and 'deny' not in action_set:
      continue                                        # Routing object contains only permits, that's OK

    rp_create_permit_deny_objects(rpo_name)
    rp_update_routing_policies(rpo_name)
    node.routing[o_name].pop(rpo_name,None)           # Finally, remove the original routing policy object

"""
Check the values in community list entries
"""
def clist_check(node: Box) -> None:
  for cname,cdata in node.routing.community.items():  # Iterate over all community lists
    for centry in cdata.value:                        # ... checking their items
      if centry.get('regexp',None) == '.*':           # "permit any" has to be rewritten
        centry.regexp = '.*:.*' if cdata.type == 'standard' else '.*:.*:.*'
        centry._value = centry.regexp                 # ... for standard or large communities
        continue
      centry._value = centry._value.strip('_')        # Remove leading/trailing boundary markers
      if ' ' in centry._value or '_' in centry._value:
        report_quirk(                                 # Also, IOS XR cannot handle multi-community entries
          f'Community lists can match a single community in each entry',
          more_data=[f'Node {node.name} community list {cname} entry {centry._value}'],
          quirk=f'routing_clist_multiple',
          category=log.IncorrectValue,
          node=node)

class IOSXR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if 'routing' in node:
      rp_set(node,'prefix',None)
      rp_set(node,'aspath',None)
      if 'community' in node.routing:
        clist_check(node)
        rp_set(node,'community','value')
