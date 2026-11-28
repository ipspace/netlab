import json

import pytest

from netsim.cli import inspect
from netsim.data import get_box


@pytest.mark.parametrize(
  ('expression', 'expected'),
  [
    ('nodes.r1.device', 'frr'),
    ('nodes.r1.enabled', True),
    ('nodes.r1.value', None),
    ('len(nodes)', 1),
    ('list(nodes.keys())', ['r1']),
    ('nodes.r1', {'device': 'frr', 'enabled': True, 'value': None}),
  ],
)
def test_xform_inspect_json_output(
  expression: str,
  expected: object,
  monkeypatch: pytest.MonkeyPatch,
  capsys: pytest.CaptureFixture[str],
) -> None:
  topology = get_box({'nodes': {'r1': {'device': 'frr', 'enabled': True, 'value': None}}})
  monkeypatch.setattr(inspect, 'load_data_source', lambda args: topology)

  inspect.run(['--format', 'json', expression])

  assert json.loads(capsys.readouterr().out) == expected
