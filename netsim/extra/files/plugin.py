from box import Box
from netsim.data import filemaps,append_to_list
from netsim.data.types import must_be_dict
from netsim.utils import log
from pathlib import Path

"""
Restructure 'files' dictionary into a list of files to avoid Box-dotting
problems
"""
def restructure_files(topology: Box) -> None:
  if not isinstance(topology.files,Box):
    return                                            # Everything else will be handled in attribute validation code

  f_dict = filemaps.box_to_dict(topology.files)       # Recover the original data structure
  f_list = [ {'path': k, 'content': v} 
               for k,v in f_dict.items() ]            # Create normalized list-based data structure
  topology.files = f_list                             # Replace dict with list

"""
Change the 'configlets' into list of files
"""
def restructure_configlets(topology: Box) -> None:

  def build_files(cfg: Box, path: str) -> None:       # Recursively transform configlets dictionary into files
    for k,v in cfg.items():                           # Iterate over dictionary contents
      separator = '' if path.endswith('/') else \
                  '-' if k in topology.defaults.providers else '.'
      if k != 'content':                              # If this is not a 'raw content' element
        k_path = path + separator + k                 # ... add next bit to file name (provider is prefixed with '-')
      else:
        k_path = path
      if isinstance(v,str):                           # Did we get to the end of the tree?
        append_to_list(                               # Add a new file to the list of files
          topology,                                   # ... file path is created from the dictionary structure
          'files',                                    # ... with '.j2' suffix because it's a template
          {'path': k_path+'.j2', 'content': v})       # ... and the file content is the value
      elif isinstance(v,Box):                         # Do we need to go further down the dictionary?
        build_files(v,k_path)                         # ... recursively do the same thing
      else:                                           # Nothing else but str or dict makes sense
        log.error(
          f'Configlet {k_path} should be a string value',
          category=log.IncorrectType,
          module='files')

  if not must_be_dict(topology,'configlets','',create_empty=False):
    return                                            # Check that the value is really a dict

  for k,v in topology.configlets.items():             # Iterate over configlets
    if isinstance(v,str):                             # Simple file with no options?
      append_to_list(                                 # Add content to the list of files
        topology,
        'files',
        {'path': k+'.j2', 'content': v })
    elif isinstance(v,Box):                           # Config template with options, has to be a directory
      build_files(v,k+'/')
    else:
      log.error(
        f'Configlet {k} should be a dictionary or a string',
        category=log.IncorrectType,
        module='files')

  topology.pop('configlets',None)                     # We no longer need this

"""
Restructure the 'files' and 'configlets'
"""
def init(topology: Box) -> None:
  output_hook = False
  if 'files' in topology:
    restructure_files(topology)
    output_hook = True
  if 'configlets' in topology:
    restructure_configlets(topology)
    output_hook = True

  if output_hook:
    append_to_list(topology.defaults.netlab.create,'output','files')

"""
Create the output files when called from 'netlab create'
"""
def output(topology: Box) -> None:
  f_list = topology.get('files',[])
  if not f_list:                                            # No files to create, we're done ;)
    return

  for file in f_list:                                       # Try to create individual files
    try:
      filepath = Path(file.path)
      filepath.parent.mkdir(parents=True, exist_ok=True)    # Create parent directories if needed
      filepath.write_text(file.content)                     # Write file content
      log.info(text=f'Created {file.path}',module='files')  # ... and report success
    except Exception as ex:                                 # ... or failure
      log.error(f'Cannot create {file.path}: {str(ex)}',category=log.FatalError,module='files')

  # Create the list of extra files that 'netlab down --cleanup' should remove
  topology._cleanup.files = [ file.path for file in f_list ]
