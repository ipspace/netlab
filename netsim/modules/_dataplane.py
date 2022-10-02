#
# Generic data plane routines
#
import typing
from box import Box

from .. import common
from ..data import global_vars,get_from_box

"""
build_id_set: given an object (topology or node) and a data structure within the object,
create a set of attributes used in that object

* obj: parent object (topology or node)
* dsname: name of the data structure (vlans, vrfs)
* attr: name of the attribute we're interested in (vlan, vni, rd, import, export)
* objname: name of the parent object in case we have to thrown an error message
"""

def build_id_set(obj: Box, dsname: str, attr: str, objname: str) -> set:
  if dsname in obj:
    if not isinstance(obj[dsname],dict):    # pragma: no cover
      common.fatal(f'Found a {dsname} setting that is not a dictionary in {objname}','dataplane')
      return set()

    return { 
      v[attr]
        for v in obj[dsname].values() 
          if isinstance(v,dict) and attr in v and v[attr] is not None and not isinstance(v[attr],bool) }

  return set()

def get_id_set(name: str) -> set:
	idvar = global_vars.get(f'{name}_id')
	if not 'value' in idvar:
		idvar.value = set()
	
	return idvar.value

def create_id_set(name: str) -> set:
	idvar = global_vars.get(f'{name}_id')
	idvar.value = set()
	return idvar.value

def extend_id_set(name: str, add_set: set) -> set:
	idset = get_id_set(name)
	idset.update(add_set)
	return idset

def set_id_counter(name: str, start: int, max_value: int = 4096) -> int:
	idvar = global_vars.get(f'{name}_id')
	idvar.next = start
	idvar.max = max_value
	return start

def get_next_id(name: str) -> int:
	idvar = global_vars.get(f'{name}_id')
	if not 'next' in idvar:
		common.fatal(f'Initial {name} value is not set, get_next_id failed')
	while True:
		if not idvar.next in idvar.value:
			idvar.value.add(idvar.next)
			return idvar.next

		idvar.next = idvar.next + 1
		if idvar.next > idvar.max:
			common.fatal(f'Ran out of {name} values, next value would be greater than {idvar.max}')
