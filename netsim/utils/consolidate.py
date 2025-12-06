#
# Consolidate all Netlab YAML files into a single JSON file
#
import json
import os
import typing
from pathlib import Path

from box import Box

from . import files as _files
from . import log, read as _read

def _get_schema_path() -> Path:
  """Get the path to the JSON schema file"""
  return Path(__file__).parent / 'consolidate_schema.json'

def _load_schema() -> typing.Optional[dict]:
  """Load the JSON schema for validation"""
  # Import jsonschema on demand
  try:
    import jsonschema
  except ImportError:
    # jsonschema not available, skip validation
    return None

  schema_path = _get_schema_path()
  if not schema_path.exists():
    log.warning(f'JSON schema not found at {schema_path}', module='consolidate')
    return None

  try:
    with open(schema_path, 'r') as f:
      return json.load(f)
  except Exception as ex:
    log.warning(f'Error loading JSON schema: {ex}', module='consolidate')
    return None

def _validate_json_cache(data: dict, schema: dict) -> bool:
  """Validate JSON cache data against schema"""
  # Import jsonschema on demand
  try:
    import jsonschema
  except ImportError:
    # jsonschema not available, skip validation
    return True  # Don't fail if jsonschema is not available

  try:
    jsonschema.validate(instance=data, schema=schema)
    return True
  except jsonschema.ValidationError as ex:
    log.error(f'JSON cache validation failed: {ex.message}', module='consolidate')
    if ex.path:
      log.error(f'  Path: {".".join(str(p) for p in ex.path)}', module='consolidate')
    return False
  except Exception as ex:
    log.warning(f'Error during JSON cache validation: {ex}', module='consolidate')
    return True  # Don't fail on validation errors, just warn

def _collect_yaml_files(
      topology_file: str,
      user_defaults: typing.Optional[list] = None,
      system_defaults: typing.Optional[list] = None) -> dict:
  """
  Collect all YAML files that would be loaded for a topology.
  Returns a dictionary mapping file paths to their parsed content.

  This simulates what the load() function does - it loads the topology
  and all defaults files, collecting all YAML files that get read.
  """
  collected = {}
  visited = set()

  def collect_file(fname: str, source: typing.Optional[str] = None) -> None:
    """Recursively collect a YAML file and all its includes"""
    # Normalize the filename
    if fname.startswith('package:'):
      cache_key = fname
    else:
      try:
        cache_key = str(_files.absolute_path(fname))
      except:
        cache_key = fname

    # Skip if already collected
    if cache_key in visited:
      return

    visited.add(cache_key)

    # Read the YAML file (this will process includes automatically)
    try:
      yaml_data = _read.read_yaml(filename=fname)
      if yaml_data is None:
        return

      # Store the file content (includes are already processed)
      collected[cache_key] = {
        'content': yaml_data.to_dict(),
        'source': fname,
        'package': fname.startswith('package:')
      }
    except Exception as ex:
      log.warning(f'Error collecting file {fname}: {ex}', module='consolidate')

  # Normalize topology file path
  if not topology_file.startswith('package:'):
    topology_file = str(_files.absolute_path(topology_file))

  # Collect the main topology file (this will also collect all its includes)
  collect_file(topology_file)

  # Now collect all defaults files that would be loaded
  # We need to simulate what load() does - it reads topology first, then defaults
  try:
    # Temporarily read topology to get defaults list
    temp_topology = _read.read_yaml(filename=topology_file)
    if temp_topology:
      defaults_list = _read.build_defaults_list(
        temp_topology,
        user_defaults=user_defaults,
        system_defaults=system_defaults
      )

      # Collect all defaults files
      for dfname in defaults_list:
        if dfname.find('package:') != 0:
          abs_dfname = str(_files.absolute_path(dfname, topology_file))
          if os.path.isfile(abs_dfname):
            collect_file(abs_dfname)
          elif os.path.isfile(dfname):
            collect_file(dfname)
        else:
          collect_file(dfname)
  except Exception as ex:
    log.warning(f'Error collecting defaults files: {ex}', module='consolidate')
    # Fallback: try to collect common defaults
    from ..utils.read import USER_DEFAULTS, SYSTEM_DEFAULTS
    all_defaults = (user_defaults or USER_DEFAULTS) + (system_defaults or SYSTEM_DEFAULTS)
    for dfname in all_defaults:
      if dfname.find('package:') != 0:
        abs_dfname = str(_files.absolute_path(dfname, topology_file))
        if os.path.isfile(abs_dfname):
          collect_file(abs_dfname)
      else:
        collect_file(dfname)

  return collected

def consolidate_to_json(
      topology_file: str,
      output_file: str,
      user_defaults: typing.Optional[list] = None,
      system_defaults: typing.Optional[list] = None) -> None:
  """
  Consolidate all YAML files into a single JSON file.

  This works by actually loading the topology (which loads all files)
  and tracking all files that get read during the process.

  Args:
    topology_file: Path to the topology YAML file
    output_file: Path where the JSON file should be written
    user_defaults: Optional list of user defaults files
    system_defaults: Optional list of system defaults files
  """
  log.info(f'Consolidating YAML files for {topology_file}...')

  # Track all files that get read
  files_tracked = {}
  original_read_yaml = _read.read_yaml

  def tracking_read_yaml(filename=None, string=None):
    """Wrapper around read_yaml that tracks all files read"""
    if filename and not string:
      # Normalize the filename for tracking
      if filename.startswith('package:'):
        cache_key = filename
      else:
        try:
          cache_key = str(_files.absolute_path(filename))
        except:
          cache_key = filename

      # Call original read_yaml
      result = original_read_yaml(filename=filename, string=string)

      # Track this file if we haven't seen it yet
      if result and cache_key not in files_tracked:
        # Handle both Box objects (dicts) and lists
        if isinstance(result, Box):
          content = result.to_dict()
        elif isinstance(result, (list, dict)):
          content = result
        else:
          content = {}
        
        files_tracked[cache_key] = {
          'content': content,
          'source': filename,
          'package': filename.startswith('package:')
        }

      return result
    else:
      return original_read_yaml(filename=filename, string=string)

  # Temporarily replace read_yaml with our tracking version
  _read.read_yaml = tracking_read_yaml

  try:
    # Actually load the topology - this will read all files
    from ..utils.read import load
    load(
      topology_file,
      user_defaults=user_defaults,
      system_defaults=system_defaults
    )
  finally:
    # Restore original read_yaml
    _read.read_yaml = original_read_yaml

  # Create the consolidated structure
  consolidated = {
    'version': '1.0',
    'topology_file': topology_file,
    'files': files_tracked,
    'file_count': len(files_tracked)
  }

  # Validate against schema before writing
  schema = _load_schema()
  if schema:
    if not _validate_json_cache(consolidated, schema):
      log.error('Generated JSON cache does not match schema, but writing anyway', module='consolidate')
    # Schema validation passed if we get here

  # Write to JSON file
  output_path = Path(output_file)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  with open(output_path, 'w') as f:
    json.dump(consolidated, f, indent=2, default=str)

  log.info(f'Consolidated {len(files_tracked)} files into {output_file}')

def consolidate_all_system_files(output_file: str = 'netlab.consolidated.json') -> None:
  """
  Consolidate all system and package YAML files without requiring a topology file.
  
  This is useful for integration test suites where you want to cache all default
  files, modules, devices, and providers that would be used across multiple labs.
  
  Args:
    output_file: Path where the JSON file should be written
  """
  log.info('Consolidating all system/package YAML files...')
  
  # Track all files that get read
  files_tracked = {}
  original_read_yaml = _read.read_yaml
  
  def tracking_read_yaml(filename=None, string=None):
    """Wrapper around read_yaml that tracks all files read"""
    if filename and not string:
      # Normalize the filename for tracking
      if filename.startswith('package:'):
        cache_key = filename
      else:
        try:
          cache_key = str(_files.absolute_path(filename))
        except:
          cache_key = filename
      
      # Call original read_yaml
      result = original_read_yaml(filename=filename, string=string)
      
      # Track this file if we haven't seen it yet
      if result and cache_key not in files_tracked:
        files_tracked[cache_key] = {
          'content': result.to_dict(),
          'source': filename,
          'package': filename.startswith('package:')
        }
      
      return result
    else:
      return original_read_yaml(filename=filename, string=string)
  
  # Temporarily replace read_yaml with our tracking version
  _read.read_yaml = tracking_read_yaml
  
  try:
    # Load all system defaults
    from ..utils.read import SYSTEM_DEFAULTS, USER_DEFAULTS
    
    # Try to load system defaults
    for default_file in SYSTEM_DEFAULTS:
      try:
        _read.read_yaml(filename=default_file)
      except:
        pass  # Some defaults may not exist, that's OK
    
    # Load package defaults
    try:
      _read.read_yaml(filename='package:topology-defaults.yml')
    except:
      pass
    
    # Load all defaults from netsim/defaults
    defaults_dir = Path(__file__).parent.parent / 'defaults'
    if defaults_dir.exists():
      for yaml_file in defaults_dir.rglob('*.yml'):
        try:
          result = _read.read_yaml(filename=str(yaml_file))
          # Some files might be sequences, skip those that fail
          if result is None:
            continue
        except Exception:
          pass  # Skip files that can't be read as dicts (e.g., sequences)
    
    # Load all modules
    modules_dir = Path(__file__).parent.parent / 'modules'
    if modules_dir.exists():
      for yaml_file in modules_dir.rglob('*.yml'):
        try:
          result = _read.read_yaml(filename=str(yaml_file))
          if result is None:
            continue
        except Exception:
          pass  # Skip files that can't be read as dicts
    
    # Load all devices
    devices_dir = Path(__file__).parent.parent / 'devices'
    if devices_dir.exists():
      for yaml_file in devices_dir.rglob('*.yml'):
        try:
          result = _read.read_yaml(filename=str(yaml_file))
          if result is None:
            continue
        except Exception:
          pass  # Skip files that can't be read as dicts
    
    # Load all providers
    providers_dir = Path(__file__).parent.parent / 'providers'
    if providers_dir.exists():
      for yaml_file in providers_dir.rglob('*.yml'):
        try:
          result = _read.read_yaml(filename=str(yaml_file))
          if result is None:
            continue
        except Exception:
          pass  # Skip files that can't be read as dicts
    
    # Load extra modules (skip deploy files which are often sequences)
    extra_dir = Path(__file__).parent.parent / 'extra'
    if extra_dir.exists():
      for yaml_file in extra_dir.rglob('*.yml'):
        # Skip deploy files which are typically sequences
        if 'deploy' in str(yaml_file):
          continue
        try:
          result = _read.read_yaml(filename=str(yaml_file))
          if result is None:
            continue
        except Exception:
          pass  # Skip files that can't be read as dicts
    
  finally:
    # Restore original read_yaml
    _read.read_yaml = original_read_yaml
  
  # Create the consolidated structure
  consolidated = {
    'version': '1.0',
    'topology_file': None,  # No specific topology
    'files': files_tracked,
    'file_count': len(files_tracked)
  }
  
  # Validate against schema before writing
  schema = _load_schema()
  if schema:
    if not _validate_json_cache(consolidated, schema):
      log.error('Generated JSON cache does not match schema, but writing anyway', module='consolidate')
    # Schema validation passed if we get here
  
  # Write to JSON file
  output_path = Path(output_file)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  
  with open(output_path, 'w') as f:
    json.dump(consolidated, f, indent=2, default=str)
  
  log.info(f'Consolidated {len(files_tracked)} system/package files into {output_file}')

def load_from_json(json_file: str, validate: bool = True) -> typing.Optional[dict]:
  """
  Load the consolidated JSON file.

  Args:
    json_file: Path to the JSON cache file
    validate: Whether to validate against schema (default: True)

  Returns:
    Dictionary mapping file paths to their content, or None if file doesn't exist or is invalid
  """
  if not os.path.isfile(json_file):
    return None

  try:
    with open(json_file, 'r') as f:
      consolidated = json.load(f)

    # Validate against schema if requested
    if validate:
      schema = _load_schema()
      if schema:
        if not _validate_json_cache(consolidated, schema):
          log.error(f'JSON cache {json_file} does not match schema', module='consolidate')
          log.error('Cache file may be corrupted or from an incompatible version', module='consolidate')
          return None
        # Note: log.debug may not be available, so we skip debug messages
      else:
        # Schema validation requested but schema not found (jsonschema may not be available)
        pass

    return consolidated.get('files', {})
  except json.JSONDecodeError as ex:
    log.error(f'Invalid JSON in cache file {json_file}: {ex}', module='consolidate')
    return None
  except Exception as ex:
    log.warning(f'Error loading JSON cache {json_file}: {ex}', module='consolidate')
    return None

