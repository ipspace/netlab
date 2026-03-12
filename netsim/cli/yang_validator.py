#
# YANG validation module for topology files
#
import json
import re
import traceback
import typing
from pathlib import Path

from box import Box

from ..utils import files as _files
from ..utils import log


def topology_to_json(topology: Box) -> dict:
  """
  Convert topology Box structure to JSON-compatible dictionary for YANG validation
  
  yangson expects JSON data matching the YANG model structure. The data should
  be wrapped in the namespace-qualified container name.
  """
  # Convert Box to dict and handle special cases
  topo_dict = topology.to_dict()
  
  # Remove all internal/private keys starting with '_' before YANG validation
  # Recursively remove underscore-prefixed keys from nested structures
  def remove_underscore_keys(obj: typing.Any, depth: int = 0) -> None:
    if depth > 10:  # Prevent infinite recursion
      return
    if isinstance(obj, dict):
      keys_to_remove = []
      for key in obj.keys():
        if key.startswith('_'):
          keys_to_remove.append(key)
        else:
          # Recursively process nested structures
          remove_underscore_keys(obj[key], depth + 1)
      # Remove underscore-prefixed keys
      for key in keys_to_remove:
        del obj[key]
    elif isinstance(obj, list):
      for item in obj:
        remove_underscore_keys(item, depth + 1)
  
  remove_underscore_keys(topo_dict)
  
  # Transform nodes from dictionary to list format for YANG validation
  # YANG lists must be arrays, but netlab uses dictionaries keyed by node name
  if 'nodes' in topo_dict and isinstance(topo_dict['nodes'], dict):
    nodes_list = []
    for node_name, node_data in topo_dict['nodes'].items():
      if isinstance(node_data, dict):
        node_data['name'] = node_name
        nodes_list.append(node_data)
      else:
        # If node_data is not a dict, create a simple node entry
        nodes_list.append({'name': node_name})
    topo_dict['nodes'] = nodes_list
  
  
  # Wrap in namespace container for YANG validation
  # yangson expects the data under the namespace-qualified container name
  return {
    'netlab-topology:topology': topo_dict
  }


def load_yang_model_path(model_path: str) -> Path:
  """
  Get Path object for YANG model file
  """
  if 'package:' in model_path:
    pkg_files = _files.get_traversable_path('package:')
    model_file = pkg_files.joinpath(model_path.replace('package:', ''))
    if not model_file.exists():
      raise FileNotFoundError(f'YANG model not found: {model_path}')
    return model_file
  else:
    model_file = Path(model_path)
    if not model_file.exists():
      raise FileNotFoundError(f'YANG model not found: {model_path}')
    return model_file


def _create_yang_library(yang_content: str) -> str:
  """
  Extract module metadata from YANG content and create YANG library JSON.
  
  Returns JSON string in ietf-yang-library format.
  """
  # Extract module name, revision, and namespace from YANG content
  mod_match = re.search(r'module\s+(\S+)\s*\{', yang_content)
  rev_match = re.search(r'revision\s+(\S+)\s*\{', yang_content)
  ns_match = re.search(r'namespace\s+"([^"]+)"', yang_content)
  
  if not mod_match:
    raise ValueError("Failed to extract module name from YANG file")
  if not rev_match:
    raise ValueError("Failed to extract revision from YANG file")
  if not ns_match:
    raise ValueError("Failed to extract namespace from YANG file")
  
  mod_name = mod_match.group(1)
  mod_revision = rev_match.group(1)
  mod_namespace = ns_match.group(1)
  
  # Create YANG library JSON (ietf-yang-library format)
  yang_library = {
    "ietf-yang-library:modules-state": {
      "module-set-id": "netlab-topology-set",
      "module": [
        {
          "name": mod_name,
          "revision": mod_revision,
          "namespace": mod_namespace,
          "conformance-type": "implement"
        }
      ]
    }
  }
  
  return json.dumps(yang_library)


def validate_topology_yang(topology: Box, yang_model_path: str) -> typing.List[str]:
  """
  Validate topology against YANG model using actual YANG MUST statements
  
  Uses yangson library to parse the YANG model and validate the topology data,
  including evaluation of MUST statements.
  
  Returns list of error messages, empty list if validation passes
  """
  errors: typing.List[str] = []
  
  # Check if yangson is available
  try:
    from yangson import DataModel  # type: ignore[import-untyped]
    from yangson.enumerations import ContentType, ValidationScope  # type: ignore[import-untyped]
    from yangson.exceptions import SchemaError, SemanticError, YangTypeError  # type: ignore[import-untyped]
  except ImportError as ex:
    log.fatal(
      f'yangson library not found: {ex}. Install it with: pip install yangson',
      module='yang'
    )
    return errors
  
  # Load YANG model file
  try:
    yang_model_file = load_yang_model_path(yang_model_path)
  except FileNotFoundError as ex:
    log.fatal(f'YANG model not found: {ex}', module='yang')
    return errors
  
  # Read YANG model file content
  try:
    with yang_model_file.open('r') as f:
      yang_content = f.read()
  except Exception as ex:
    log.fatal(f'Failed to read YANG model file: {ex}', module='yang')
    return errors
  
  # Create data model from YANG file
  # yangson requires YANG library JSON format, not raw YANG files
  yang_dir = str(yang_model_file.parent)
  
  try:
    yang_library_json = _create_yang_library(yang_content)
    dm = DataModel(yang_library_json, [yang_dir])
  except SchemaError as ex:
    log.fatal(f'Failed to load YANG model: {ex}', module='yang')
    return errors
  except ValueError as ex:
    log.fatal(f'Invalid YANG model format: {ex}', module='yang')
    return errors
  except Exception as ex:
    log.fatal(f'Failed to create YANG data model: {ex}', module='yang')
    return errors
  
  # Convert topology to JSON format and validate
  try:
    topo_json = topology_to_json(topology)
    instance = dm.from_raw(topo_json)
    instance.validate(ValidationScope.all, ContentType.all)
  except (SemanticError, YangTypeError) as ex:
    # These are expected validation errors - return them as error messages
    errors.append(f"YANG validation failed: {str(ex)}")
  except Exception as ex:
    errors.append(f"YANG validation failed: {str(ex)}")
    if log.debug_active('yang'):
      errors.append(f"Traceback: {traceback.format_exc()}")
  
  return errors



