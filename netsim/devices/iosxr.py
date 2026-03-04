#
# Cisco IOS-XR quirks
#
import typing

from box import Box

from ..data import get_new_box
from . import _Quirks, report_quirk

"""
Split prefix lists into permit_ and deny_ sets and adjust the routing policies accordingly
"""
def rp_set(node: Box, o_name: str, o_value: typing.Optional[str]) -> None:
  if o_name not in node.routing:                      # Routing policy object not used, nothing to do
    return

  rp_match = f'match.{o_name}'                        # This is how we're matching the object in routing policies
  for rpo_name in list(node.routing[o_name].keys()):  # Iterate over routing objects
    rpo_value = node.routing[o_name][rpo_name]        # Get the list value from the object
    if o_value:                                       # ... or one of its attributes
      rpo_value = rpo_value[o_value]

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

    if len(action_set) <= 1 and 'deny' not in action_set:
      continue                                        # Routing object contains only permits, that's OK

    for action in ('deny','permit'):
      o_act_name = f'{rpo_name}_{action}'             # Create permit- and deny objects
      o_act_list = [ entry for entry in rpo_value if entry.action == action ]
      if o_value:                                     # Do we have to replace an attribute?
        o_act_value = get_new_box(node.routing[o_name][rpo_name])
        o_act_value[o_value] = o_act_list             # Copy the original object and replace the list value
        node.routing[o_name][o_act_name] = o_act_value
      else:
        node.routing[o_name][o_act_name] = o_act_list # Otherwise the trimmed list is the value

    # Now we have to update routing policies
    for rp_value in node.routing.get('policy',{}).values():
      for rp_entry in rp_value:                       # Iterate over RP entrie
        if rp_match not in rp_entry:                  # Are we matching on current object type?
          continue
        if rp_entry[rp_match] != rpo_name:            # ... and using the current object?
          continue
        for kw in ('deny','permit'):                  # Create an extra attribute with permit/deny names
          rp_entry.match[f'_xr_{o_name}'][kw] = f'{rpo_name}_{kw}'
        rp_entry.pop(rp_match)                        # And remove the original attribute

    node.routing[o_name].pop(rpo_name,None)           # Finally, remove the original routing policy object

class IOSXR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if 'routing' in node:
      rp_set(node,'prefix',None)
