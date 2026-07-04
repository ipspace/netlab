from box import Box


def get_key_paths(data: Box, path: str='', k_list: list = []) -> list:
  for k,v in data.items():
    if isinstance(v,Box):
      get_key_paths(v,f'{path}{"." if path else ""}{k}',k_list)
    else:
      k_list.append(f'{path}.{k}')

  return k_list

def init(topology: Box) -> None:
  d_list = []
  for ndata in topology.nodes.values():                     # Collect the devices from nodes
    if not isinstance(ndata,Box):
      continue
    if 'device' in ndata and ndata.device not in d_list:
      d_list.append(ndata.device)

  for gname,gdata in topology.get('groups',{}).items():     # Collect data from groups
    if gname.startswith('_') or not isinstance(gdata,Box):
      continue
    if 'device' in gdata and gdata.device not in d_list:
      d_list.append(gdata.device)

  if 'device' in topology.defaults and topology.defaults.device not in d_list:
    d_list.append(topology.defaults.device)

  for node,ndata in topology.nodes.items():                 # Collect the devices in the lab topology
    if 'device' in ndata and ndata.device not in d_list:
      d_list.append(ndata.device)

  for device in d_list:                                     # Now try to do the fixups
    f_data = topology.get(f'_fixup.{device}',None)          # Get the fixup data
    if f_data is None:                                      # No fixup for this device?
      continue                                              # Perfect, move on

    if '_delete' in f_data:                                 # Do we have to delete stuff?
      for key in get_key_paths(f_data._delete):             # Get the paths to delete
        topology.pop(key,None)                              # ... remove individual attributes
        print(f'Fixup for {device}: deleting {key}')        # ... and create warnings
      f_data.pop('_delete',None)

    for k,v in f_data.items():                              # Now iterate over the remaining attributes
      if isinstance(v,Box):                                 # to do a merge-in-place
        topology[k] = topology[k] + v                       # ... dictionaries are merged
      else:
        topology[k] = v                                     # ... while simple values are replaced

    print(f'Fixup for {device}: modifying {",".join(f_data.keys())}')
