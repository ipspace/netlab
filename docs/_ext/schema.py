"""
Sphinx extension that writes the JSON schema of lab topologies (netlab show schema --system)
into the root of the HTML documentation, so the published schema always matches the code
the documentation describes.
"""

import contextlib
import io
import os
import typing

from netsim.cli import show

SCHEMA_FILE = 'topology.schema.json'

def write_schema(app: typing.Any, exception: typing.Optional[Exception]) -> None:
  if exception is not None or app.builder.format != 'html':
    return

  with contextlib.redirect_stdout(io.StringIO()) as schema:
    show.run([ 'schema', '--system' ])

  with open(os.path.join(app.outdir,SCHEMA_FILE),'w') as output:
    output.write(schema.getvalue())

def setup(app: typing.Any) -> dict[str, object]:
  app.connect('build-finished',write_schema)
  return {
    "version": "0.1",
    "parallel_read_safe": True,
    "parallel_write_safe": True,
  }
