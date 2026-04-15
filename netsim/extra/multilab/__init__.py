from pathlib import Path

from box import Box

from netsim import data
from netsim.augment import devices
from netsim.utils import log, strings

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
        change[k] = strings.eval_format(change[k],ctx_data)

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
Implement file-based mutex locking of provider start/stop commands
"""
def change_up_down(pdata: Box, lock: str, path: str) -> None:
  for kw in ['start','stop']:
    if kw not in pdata:
      continue
    if not pdata[kw]:
      continue
    if not isinstance(pdata[kw],str):
      log.warning(
        text=f'Cannot add mutex to {path}.{kw} command {pdata[kw]}',
        module='multilab')
      continue
    verbose = '--verbose -E 42' if log.VERBOSE else '-E 42'
    pdata[kw] = f'flock {verbose} {lock} {pdata[kw]}'
    if log.debug_active('plugin'):
      print(f'{path}.{kw}={pdata[kw]}')

"""
Add mutex locking to lab up/down commands
"""
def add_provider_locks(topology: Box) -> None:
  lock = data.types.must_be_str(                      # check that multilab.lock is a string
    parent=topology.defaults.multilab,
    key='lock',
    path='defaults.multilab',
    module='multilab')
  if not lock:                                        # Error, get out of here
    return
  
  # Collect all providers used in the current topology
  defaults = topology.defaults
  pset = { devices.get_provider(node_data,defaults) for node_data in topology.nodes.values() }
  lock = str(Path(lock).resolve())                    # And resolve relative/$HOME paths in lock filename

  for pname in list(pset):                            # Iterate over all providers used in the lab topology
    pdata = defaults.providers[pname]
    change_up_down(pdata,lock,f'providers.{pname}')   # ... and change their up/down commands

    for sname in list(pset):                          # Next, iterate over all potential secondary providers
      if sname not in pdata:                          # ... pname/sname is not a valid combo
        continue
      change_up_down(pdata[sname],lock,f'providers.{pname}.{sname}')

"""
Main multilab code:

* Validate default settings
* Evaluate parameters to be changed
* Merge changed parameters into topology
"""
def init(topology: Box) -> None:
  mlab = topology.defaults.multilab
  abort = False
  for kw in ['id','change']:                          # Check that we have all default parameters needed for multilab to work
    if not kw in mlab:
      log.error(f'multilab plugin requires defaults.multilab.{kw} parameter',log.MissingValue,'multilab')
      abort = True

  if abort:
    return

  data.types.must_be_int(                             # Now validate that multilab.id is an integer less than 200
    parent=mlab,
    key='id',
    path='defaults.multilab',
    module='multilab',
    min_value=1,
    max_value=200)

  data.types.must_be_dict(                            # ... and that multilab.change is a dictionary
    parent=mlab,
    key='change',
    path='defaults.multilab',
    module='multilab')

  ctx_data = data.get_box(topology)
  ctx_data.id = mlab.id
  eval_changed_parameters(mlab.change,ctx_data)       # Evaluate changed parameters
  if log.debug_active('plugin'):                      # Print the results if we're debugging
    print(f'MULTILAB CHANGES\n==============\n{mlab.change.to_yaml()}')

  merge_changes(topology,mlab.change)                 # And merge the changes with the topology

def post_transform(topology: Box) -> None:
  if 'lock' in topology.defaults.multilab:            # If needed, add 'flock' command to provider start/stop commands
    add_provider_locks(topology)
