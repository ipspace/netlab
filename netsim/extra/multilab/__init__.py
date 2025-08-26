import typing

from box import Box

from netsim import data, utils

"""
Depth-first evaluation of changed parameters:

* Iterate over the dictionary of changes
* Recurse if the value is a dictionary
* Evaluate a string value as formatted string
* Skip everything else (until someone figures out we need more)
"""
def eval_changed_parameters(change: Box, ctx_data: Box) -> None:
  for k in list(change.keys()):
    if isinstance(change[k],Box):
      eval_changed_parameters(change[k],ctx_data)
    elif isinstance(change[k],str):
      if '{' in change[k]:
        change[k] = utils.strings.eval_format(change[k],ctx_data)

"""
Merge changed parameters evaluated by multilab into the lab topology

The changes have to be made 'in place' as we cannot return new topology from
plugin initialization code.
"""
def merge_changes(topology: Box, change: Box) -> None:
  for k in list(change.keys()):                                       # Iterate over changed parameters
    if isinstance(change[k],Box) and isinstance(topology[k],Box):     # Merging a hierarchical data structure into topology dictionary?
      topology[k] = topology[k] + change[k]                           # ... easy task, Box addition saves the day
    elif isinstance(change[k],list) and isinstance(topology[k],list): # We can add the changed list to the original list
      topology[k].extend(change[k])
    else:                                                             # Otherwise overwrite the original value. Bad luck.
      topology[k] = change[k]

"""
Main multilab code:

* Validate default settings
* Evaluate parameters to be changed
* Merge changed parameters into topology
"""
def init(topology: Box) -> None:
  mlab = topology.defaults.multilab
  abort = False
  for kw in ['id','change']:                                          # Check that we have all default parameters needed for multilab to work
    if not kw in mlab:
      utils.log.error(f'multilab plugin requires defaults.multilab.{kw} parameter',utils.log.MissingValue,'multilab')
      abort = True

  if abort:
    return

  data.types.must_be_int(                                             # Now validate that multilab.id is an integer less than 200
    parent=mlab,
    key='id',
    path='defaults.multilab',
    module='multilab',
    min_value=1,
    max_value=200)

  data.types.must_be_dict(                                            # ... and that multilab.change is a dictionary
    parent=mlab,
    key='change',
    path='defaults.multilab',
    module='multilab')

  ctx_data = data.get_box(topology)
  ctx_data.id = mlab.id
  eval_changed_parameters(mlab.change,ctx_data)                       # Evaluate changed parameters
  if utils.log.debug_active('plugin'):                                # Print the results if we're debugging
    print(f'MULTILAB CHANGES\n==============\n{mlab.change.to_yaml()}')

  merge_changes(topology,mlab.change)                                 # And merge the changes with the topology
