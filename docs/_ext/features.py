"""
Sphinx extension implementing the *features* directive.

The directive takes a comma-separated list of ``feature=header`` parameters.
Each parameter defines one column of a table: *feature* is the machine-readable
feature name used by the code populating the table body, *header* is the
human-readable column header.

Usage::

    .. features:: vlan=VLAN support, vrf=VRF support, mpls=MPLS support
"""

from typing import Any

from docutils import nodes
from docutils.parsers.rst import Directive


class Features(Directive):
  """Create a table with one column per feature parameter."""

  required_arguments = 1
  optional_arguments = 0
  final_argument_whitespace = True
  has_content = False

  def run(self) -> list[nodes.Node]:
    features = self._parse_features()
    return [self._build_table(features)]

  def _parse_features(self) -> dict[str, str]:
    features = {}
    for parameter in self.arguments[0].split(","):
      name, separator, header = parameter.partition("=")
      name = name.strip()
      header = header.strip()
      if not separator or not name or not header:
        raise self.error(f"Invalid feature parameter '{parameter.strip()}', expected 'feature=header'")
      features[name] = header
    return features

  def _build_table(self, features: dict[str, str]) -> nodes.table:
    table = nodes.table()
    tgroup = nodes.tgroup(cols=len(features))
    table += tgroup
    for _ in features:
      tgroup += nodes.colspec(colwidth=1)
    thead = nodes.thead()
    tgroup += thead
    header_row = nodes.row()
    thead += header_row
    for header in features.values():
      header_row += self._build_cell(header)
    tgroup += nodes.tbody()
    return table

  def _build_cell(self, text: str) -> nodes.entry:
    entry = nodes.entry()
    paragraph = nodes.paragraph()
    paragraph += nodes.Text(text)
    entry += paragraph
    return entry


def setup(app: Any) -> dict[str, object]:
  app.add_directive("features", Features)
  return {
    "version": "0.1",
    "parallel_read_safe": True,
    "parallel_write_safe": True,
  }
