#
# Lab topology JSON schema tests
#
# * The published schema must match the attribute definitions
# * The schema must accept every transformation test topology
# * The schema must catch common mistakes
#

import contextlib
import functools
import glob
import io
import json
import pathlib
import typing

import jsonschema
import pytest
import yaml

from netsim.cli import show

SCHEMA_FILE = pathlib.Path('../docs/_extra/topology.schema.json')

# Plugins that transform the lab topology before validation and don't define their attributes
UNDEFINED_PLUGIN_ATTRIBUTES = [ 'node.clone' ]

@functools.lru_cache
def generate_schema(plugins: typing.Tuple[str, ...] = ()) -> str:
  cli_args = [ 'schema', '--system' ]
  if plugins:
    cli_args += [ '--plugin', *plugins ]
  with contextlib.redirect_stdout(io.StringIO()) as output:
    show.run(cli_args)
  return output.getvalue()

@functools.lru_cache
def schema_validator(plugins: typing.Tuple[str, ...] = ()) -> jsonschema.Draft7Validator:
  return jsonschema.Draft7Validator(json.loads(generate_schema(plugins)))

def test_schema_is_current() -> None:
  if SCHEMA_FILE.read_text() != generate_schema():
    pytest.fail(
      f'{SCHEMA_FILE} does not match the attribute definitions, '+
      f'run "netlab show schema --system > docs/_extra/topology.schema.json"',
      pytrace=False)

def test_schema_is_valid() -> None:
  jsonschema.Draft7Validator.check_schema(json.loads(SCHEMA_FILE.read_text()))

def extends_attributes(data: typing.Any, path: str = '') -> bool:
  """
  Lab topologies can define custom attributes in defaults, the schema can't know them
  """
  if not isinstance(data,dict):
    return False
  for k,v in data.items():
    k_path = f'{path}.{k}' if path else str(k)
    if k_path.startswith('defaults') and 'attributes' in k_path.split('.'):
      return True
    if extends_attributes(v,k_path):
      return True
  return False

@pytest.mark.parametrize('test_case',sorted(glob.glob('topology/input/*yml')))
def test_schema_accepts_topology(test_case: str) -> None:
  topology = yaml.safe_load(pathlib.Path(test_case).read_text())
  if extends_attributes(topology):
    pytest.skip('lab topology defines custom attributes')

  plugins = topology.get('plugin',[])
  if set(plugins) & set(UNDEFINED_PLUGIN_ATTRIBUTES):
    pytest.skip('plugin attributes are not defined')
  validator = schema_validator(tuple(plugins if isinstance(plugins,list) else [ plugins ]))
  error = jsonschema.exceptions.best_match(validator.iter_errors(topology))
  if error is not None:
    pytest.fail(f'{test_case}: {error.json_path}: {error.message}',pytrace=False)

@pytest.mark.parametrize('topology',[
  'nodes: { r1: { devce: eos } }',
  'nodes: { r1: { device: no_such_device } }',
  'module: [ ospff ]',
  'nodes: { r1: { bgp: { ass: 65000 } } }',
  'links: [ { r1: {}, r2: {}, type: ptp } ]',
  'vlans: { red: { id: 5000 } }',
  'provider: no_such_provider',
  'nodess: [ r1 ]',
])
def test_schema_rejects_topology(topology: str) -> None:
  if schema_validator().is_valid(yaml.safe_load(topology)):
    pytest.fail(f'The schema accepts an invalid topology: {topology}',pytrace=False)
