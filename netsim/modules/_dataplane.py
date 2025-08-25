#
# Generic data plane routines
#
import typing

from box import Box

from ..data import global_vars
from ..data.types import must_be_list
from ..utils import log

"""
The ID Set routines provide a common interface to identifiers that can be auto-assigned or static:

Creating and updating the ID set:
* build_id_set -- create the set of static identifiers
* get_id_set -- get a set of already-allocated identifiers
* create_id_set -- create a global variable storing the identifier set and auto-assign sequence number
* extend_id_set -- extend an existing ID set with a set of static identifiers

Querying ID set:
* is_id_used -- check whether an ID is in the specified ID set. Consumers of this library often work
  directly with the set returned by get_id_set instead of calling this function

Auto-assign sequence numbers
* set_id_counter -- create an auto-assign counter for an ID set, specifying initial and maximum value
* get_next_id -- given a namespace (ID set, auto-assign counter), create next unused identifier
"""

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
      log.fatal(f'Found a {objname}.{dsname} setting that is not a dictionary','dataplane')
      return set()

    return { 
      v[attr]
        for v in obj[dsname].values() 
          if isinstance(v,dict)
            and attr in v
            and v[attr] is not None
            and not isinstance(v[attr],bool)
            and isinstance(v[attr],(int,str)) }

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

def is_id_used(name: str, value: typing.Any) -> bool:
	idset = get_id_set(name)
	return value in idset

def set_id_counter(name: str, start: int, max_value: int = 4096) -> int:
	idvar = global_vars.get(f'{name}_id')
	idvar.next = start
	idvar.max = max_value
	if not idvar.value:
		idvar.value = set()

	return start

def get_next_id(name: str, hint: typing.Optional[str] = None) -> int:
  idvar = global_vars.get(f'{name}_id')
  if not 'next' in idvar:
    log.fatal(f'Initial {name} value is not set, get_next_id failed')
  while True:
    if not idvar.next in idvar.value:
      idvar.value.add(idvar.next)
      return idvar.next

    idvar.next = idvar.next + 1
    if idvar.next > idvar.max:
      log.error(
        f'Ran out of {name} values, next value would be greater than {idvar.max}',
        module='dataplane',
        category=log.FatalError,
        more_hints=hint)
      log.exit_on_error()

"""
validate_object_reference_list

Validate that a list of references is valid. Create a list of all available references if there
is no list in the parent object.

Input:
* parent -- node or other parent object (topology if missing)
* parent_path -- path to display in error messages
* topology -- lab topology
* list_name -- name of reference list (example: vxlan.vlans)
* reference_dictionary -- name of dictionary with objects list_name references (example: vlans)
* reference_name -- name of objects in reference_dictionary (example: VLAN)
* create_default -- do we have to create a default list
* merge_topology -- do we have to merge topology-level list with local default list
* module -- calling module (used in error messages)
"""

def validate_object_reference_list(
			parent: typing.Optional[Box],
			topology: Box,
			list_name: str,
			reference_dictionary: str,
			reference_name: str,
			parent_path: str = 'topology',
			create_default: bool = True,
			default_filter: typing.Callable = lambda x: True,
			merge_topology: bool = True,
			module: str = 'dataplane') -> bool:

  if parent is None:
    parent = topology

  ref_list = must_be_list(
                parent=parent,
                key=list_name,
                path=parent_path,
                module=module,
                create_empty=False)                           	# If the attribute is there, it must be a list

  if not ref_list:
    if not reference_dictionary in parent:                          # If there are no local objects, we don't need the default value
      return True
    if not create_default:																					# Do we need a default value for the list?
      return True

    # Create the default list based on local objects
    ref_list = [ k for k,v in parent[reference_dictionary].items() if default_filter(v) ]
    if merge_topology:																							# Do we need to merge the object default list with topology value?
      topo_ref_list = topology.get(list_name,None)    			        # ... get global list
      if not topo_ref_list is None:
        for k in topo_ref_list:																 			# ... now carefully append global list to local one retaining element order
          if not k in ref_list:																			# ... of course we could use dirty one-line tricks, but why should we?
            ref_list.append(k)

    if not ref_list:																								# Still nothing to do? OK, get out of here
      return True

    parent[list_name] = ref_list

  list_ok = True
  for obj_name in ref_list:                                         # Now check whether the names of reference objects are valid
    if obj_name in parent.get(reference_dictionary,{}):             # ... but very carefully, we don't want to create extra boxes
      continue
    if obj_name in topology.get(reference_dictionary,{}):           # ... global name is also OK
      continue
    log.error(
      f'{list_name} refers to invalid {reference_name} {obj_name} in {parent_path}',
      log.IncorrectValue,
      module)
    list_ok = False

  return list_ok
