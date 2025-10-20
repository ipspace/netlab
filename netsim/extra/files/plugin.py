from pathlib import Path

from box import Box

from netsim.data import append_to_list, filemaps
from netsim.data.types import must_be_dict
from netsim.utils import log

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
      if k != 'base':                                 # If this is not a 'base content' element
        k_path = path + separator + k                 # ... add next bit to file name (provider is prefixed with '-')
      else:
        k_path = path
      if isinstance(v,str):                           # Did we get to the end of the tree?
        if k_path.endswith('/'):                      # Are we dealing with the 'template/base' edge case?
          k_path = k_path[:-1]                        # If so, remove '/' to create a .j2 file in lab directory
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
Change 'validation._test_.config.inline' validation elements into templates
"""
def inline_validation_templates(topology: Box) -> bool:
  found_inline = False
  if not isinstance(topology.validate,Box):           # We're in pre-validation phase, so we can't trust anything
    return False
  for t_name,test in topology.validate.items():       # Iterate over tests
    i_value = test.get('config.inline',None)          # Does this test have 'config.inline' element?
    if i_value is None:                               # Nope, we're good
      continue
    v_template = f'_v_{t_name}'                       # Configlet name is derived from test name
    topology.configlets[v_template] = i_value         # Save the template value, the next phase will take it from here
    test.config.pop('inline',None)                    # Pop the 'inline' element from test config attribute
    test.config.template = v_template                 # ... and replace it with a configlet template
    found_inline = True

  return found_inline

"""
Process 'config.inline' node- or group objects
"""
def process_inline_config(topology: Box, o_type: str) -> None:
  if o_type not in topology:                          # The object type is not in current topology
    return                                            # --> nothing to do
  if not isinstance(topology[o_type],Box):            # ... or it's not a Box. Let someone else deal with that
    return

  for o_name,o_data in topology[o_type].items():      # We got something, iterate over it
    if not isinstance(o_data,Box):                    # The data is not a Box, nothing to do, move on
      continue
    if not 'config' in o_data:                        # The object does not have a 'config' element, move on
      continue
    if not isinstance(o_data.config,Box):             # Or maybe it's a traditional 'config' element
      continue
    c_templates = []                                  # The fun part starts ;)
    c_inline = '_' + o_type[0] + '_' + o_name         # Build the name for 'inline' template
    for c_n,c_v in o_data.config.items():             # Now change the config keys/values into templates
      if c_n == 'inline':                             # Change 'inline' into object-specific template name
        c_n = c_inline
      if c_n in topology.configlets:
        log.error(
          f'{o_type} {o_name} tries to define config template {c_n} that already exists in configlets',
          category=log.IncorrectAttr,
          module='files')                             # Overlap in naming
      else:
        topology.configlets[c_n] = c_v                # Add node- or group-defined configlet
      c_templates.append(c_n)                         # ... and remember what templates the node/group uses

    o_data.config = c_templates                       # Finally, make node/group config element a list of templates

"""
Check that all 'path' attributes point to destinations within the lab directory tree
"""
def check_output_paths(topology: Box) -> None:
  lab_dir = Path('.').resolve()
  for f_entry in topology.files:                      # Now iterate over the specified files
    abs_path = Path(f_entry.path).resolve()           # Find the absolute path
    try:                                              # Try to make it a path relative to the lab directory
      abs_path.relative_to(lab_dir)
    except ValueError:
      log.error(
        f"path {f_entry.path} specified in 'files' entry#{topology.files.index(f_entry) + 1} is outside of the lab directory",
        more_hints='You cannot use the files plugin to create files outside of the lab directory',
        module='files',
        category=log.IncorrectValue)

"""
Plugin initialization:

* restructure the inline configs on groups and nodes, 'files' dictionary,
  'configlets', and validation entries
* register an output hook
"""
def init(topology: Box) -> None:
  output_hook = False
  process_inline_config(topology,'nodes')
  process_inline_config(topology,'groups')
  if 'validate' in topology:
    if inline_validation_templates(topology):
      output_hook = True
  if 'files' in topology:
    restructure_files(topology)
    output_hook = True
  if 'configlets' in topology:
    restructure_configlets(topology)
    output_hook = True
  if output_hook:
    append_to_list(topology.defaults.netlab.create,'output','files')

"""
Post-transform validation: check that all paths are within the current lab directory tree

This check does not involve any data transformation and is thus best done after the
structure of the "files" list has been checked
"""
def post_transform(topology: Box) -> None:
  if 'files' in topology:
    check_output_paths(topology)

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
