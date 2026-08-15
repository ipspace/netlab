"""
Sphinx extension implementing the *features* directive.

The directive takes a YAML-formatted list of features as its content.
See developer documentation (docs/dev/features-tables.md) for details.

Usage (from within MyST parser)::

    ```{features}
    - title: VLAN support
      enabled: bfd
    ```
"""

import typing

from box import Box, BoxList
from box.exceptions import BoxError
from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.util.parsing import nested_parse_to_nodes

from netsim.augment import devices
from netsim.data import append_to_list, get_box, get_empty_box
from netsim.utils import read as _read

SETTINGS: Box
DIRECTIVE: SphinxDirective
TABLE_COUNT: int = 0

BUILTINS: dict = {                            # Allowed built-in functions. Extend as needed ;)
  'len': len
}

def safer_eval(xpr: str, locals: Box) -> typing.Any:
  """
  We might need operators and functions in feature/caveat expressions, so we
  need to use "eval". However, we could make it a bit safer ;)
  """
  global BUILTINS

  return eval(xpr,locals=locals,globals={ '__builtins__': BUILTINS })

def table_cell(
      text: str,
      align: str = '',
      fn: typing.Optional[Box] = None) -> nodes.entry:
  """
  Add a cell to the features table. The cell can be aligned (with a CSS class),
  the cell text is split into multiple lines based on "<br>" tag, and parsed
  as Markdown to support markup like links/bold/italic. Finally, a footnote
  (specified as label/refid dict) can be added to the text.
  """
  entry = nodes.entry()                                     # Create a new cell
  if align:                                                 # If needed, assign a CSS class to it
    entry['classes'].append('text-'+align)
  para_list = []
  for line in text.split('<br>'):                           # Iterate over lines of text
    paragraph = nodes.paragraph()                           # Each line becomes a paragraph, its contents parsed as Markdown
    paragraph += nested_parse_to_nodes(DIRECTIVE.state,line,offset=DIRECTIVE.content_offset)
    para_list.append(paragraph)
  if fn:                                                    # If needed, add footnote reference to the last paragraph
    paragraph[-1] += nodes.footnote_reference(text=fn.label,refid=fn.refid)
  entry += para_list                                        # ... add paragraphs to the cell
  return entry                                              # ... and return cell data structure

def features_columns(tgroup: nodes.tgroup, features: dict) -> None:
  """
  Create N+1 (device + feature list) columns for the features table. The
  columns have equal width; the table relies on browser rendering it as needed.
  """
  for _ in range(len(features)+1):
    tgroup += nodes.colspec(colwidth=1)

def create_features_table(features: dict) -> typing.Tuple[nodes.table,nodes.tgroup]:
  """
  Create the scaffolding for the features table -- a table object with
  a table group with column definitions
  """
  table = nodes.table()
  tgroup = nodes.tgroup(cols=len(features) + 1)
  table += tgroup
  features_columns(tgroup,features)
  return (table,tgroup)

def features_header(tgroup: nodes.tgroup, features: BoxList) -> None:
  """
  Create the header for the features table: a new THEAD object with a
  single row containing feature titles
  """
  thead = nodes.thead()
  tgroup += thead
  header_row = nodes.row()
  thead += header_row
  header_row += table_cell('Device')
  for header in features:
    header_row += table_cell(header.get('title','???'),align="center")

def features_body(tgroup: nodes.tgroup, device_data: typing.List[typing.List]) -> None:
  """
  Create the body of the features table passed as a row-list-of-column-data-lists.
  The column data are dicts that could have 'text' key (for verbatim text) or
  'status' key (for device has/does-not-have a feature). The elements with 'status'
  key could include 'caveat' key -- a refid to the device caveats.
  """
  tbody = nodes.tbody()                           # Create TBODY structure
  tgroup += tbody                                 # ... and append it to table group

  for d_row in device_data:                       # Next, iterate over devices
    trow = nodes.row()                            # ... creating a row for each device
    tbody += trow
    for d_data in d_row:                          # Finally, iterate over device data
      if 'text' in d_data:                        # ... verbatim text?
        trow += table_cell(d_data['text'],fn=d_data.get('fn',''))
      elif 'status' in d_data:                    # ... or status (OK/MISSING)
        txt = '✅' if d_data['status'] else '❌'
        if 'caveat' in d_data:                    # Do we have to add a caveat?
          txt += f'[❗]({d_data["caveat"]})'      # Use Markdown link to point to the caveat (MyST will resolve ref IDs)
        trow += table_cell(txt,align='center')
      else:
        trow += table_cell('🤦‍♂️')                  # None of the above, we failed miserably :()

def get_feature_row(device_data: Box, dname: str, table_def: Box) -> typing.Optional[list]:
  df_row = []                                   # ... starting with an empty row for each device
  f_valid = False                               # ... assuming the device is not relevant and should not be included
  for f_def in table_def.features:              # Ready? Now iterate over feature definitions
    try:                                        # Try to evaluate whether the device supports the feature
      f_OK = bool(safer_eval(f_def.enabled,locals=device_data))
    except Exception:                           # Failed miserably? It could be any number of reasons
      f_OK = False                              # ... but we'll just assume the device DOES NOT support the feature
    dt_value: dict = {'status': f_OK}           # Save the results
    if f_OK and 'caveats' in f_def:             # ... but wait, there's more. Do we need to check for caveats?
      try:                                      # Let's do it. Try to evaluate caveat data
        f_caveat = safer_eval(f_def.caveats,locals=device_data)
        dt_value['caveat'] = 'caveats-'+dname if f_caveat is True else f_caveat
      except Exception:                         # Failed? Looks like there's nothing to mentio ;)
        pass
    df_row.append(dt_value)                     # OK, the "feature status" is ready, append it to the device features row
    f_valid = f_valid or f_OK                   # ... and remember if the device is relevant (at least one feature is implemented)

  return df_row if f_valid else None

def get_device_features(settings: Box, table_def: Box) -> Box:
  """
  Build the per-device lists of features displayed in the table from the device
  definitions.
  """
  df_data = get_empty_box()

  for dname,ddata in settings.devices.items():    # Iterate over all devices
    f_data = ddata + ddata.features
    df_row = get_feature_row(f_data,dname,table_def)
    if df_row:                                    # Does the device supports the specified feature set?
      df_data[dname].features = df_row            # ... go and store its data
    is_daemon = ddata.get('daemon',False)         # Only clab provider is checked for daemons
    p_list = ['clab'] if is_daemon else list(settings.providers) 
    for p_name in p_list:                         # Next, check for provider-specific features
      pf_data = ddata.get(f'{p_name}.features')   # Try to fetch device.provider.features dict
      if not pf_data:                             # Not there? Cool, move on
        continue
      dpf_row = get_feature_row(f_data + pf_data,dname,table_def)
      if dpf_row and dpf_row != df_row:           # Are the per-provider features different from device ones?
        dpf_name = dname if is_daemon else f'{dname}/{p_name}'
        df_data[dpf_name].features = dpf_row      # Store as device for daemons, device/provider otherwise

  return df_data

def remove_duplicate_features(settings: Box, df_data: Box) -> None:
  """
  The craziest of them all: remove child devices that have identical features as the parent
  device (so they were probably inherited)
  """
  for dname in list(df_data.keys()):              # Iterate over all relevant devices
    ddata = settings.devices[dname]
    p_list = ddata.get('_parents',[])             # ... and get a list of device's parent
    if not p_list:                                # ... No parent? Cool.
      continue
    parent = p_list[0]                            # Here's the cool trick: the most-generic parent is always the first in the list ;)
    if parent not in df_data:                     # But it wasn't relevant? No worries, move on
      continue
    if not settings.devices[parent].get('docparent',True):
      continue                                    # Some devices (like FRR) don't want to appear as parents (for SONiC)
    if df_data[dname].features == df_data[parent].features:
      df_data.pop(dname)                          # Child and (grand?)parent have identical features? Remove the child
      append_to_list(df_data[parent],'ch_match',dname)
    else:                                         # Otherwise mark that a (grand)child has diverted from the parent
      append_to_list(df_data[parent],'ch_mismatch',dname)

def remove_meta_devices(settings: Box,df_data: Box) -> None:
  """
  Remove meta-devices (generic parents, "none" and "unknown") that have no relevant children.
  This automatically removes the "none" and "unknown" devices.
  """
  for dname in list(df_data.keys()):
    ddata = settings.devices[dname]
    if not ddata.get('_meta_device',False):       # Not a meta device? Move on...
      continue
    if 'ch_match' in df_data[dname]:              # Does the meta device has relevant children that inherited its features?
      continue                                    # The children were removed, so we have to keep the meta-device
    df_data.pop(dname)                            # ... otherwise remove it

def build_device_feature_matrix(
      settings: Box,
      df_data: Box) -> typing.Tuple[typing.List[typing.List],typing.List]:
  """
  Given the device/feature data, build the features table
  """
  global TABLE_COUNT                              # Need to count documentation-wide tables for link anchors
  TABLE_COUNT += 1

  device_data: list = []
  footnotes:   list = []                          # We might need "this parent device includes these children" footnotes

  dev_data = settings.devices
  devices: dict = {}                              # We need a lookup table for device short names
  provider_object: dict = {                       # Name of provider-specific objects
    'libvirt': 'VMs',
    'clab': 'containers'}

  def get_device_docname(dname: str) -> str:      # Helper function: get device's documentation name
    return dev_data[dname].get('docname',dev_data[dname].get('description',dname))

  device_codes = set(dev_data).union(df_data)     # Add defined devices and device/provider pairs
  for dname in device_codes:                      # Now build the device-to-docname mapping
    if '/' not in dname:                          # Simple device?
      devices[dname] = get_device_docname(dname)  # ... just store its docname
    else:                                         # Device/provider pair?
      (d_name,p_name) = dname.split('/',1)        # Extract components
      p_name = provider_object.get(p_name,p_name) # ... and map provider to provider object name
      devices[dname] = get_device_docname(d_name) + f' ({p_name})'

  label_count = 0
  dname_list = list(devices)                      # Get a list of devices sorted by docnames
  dname_list.sort(key=lambda x: devices[x].upper())
  for dname in dname_list:                        # Finally! Iterate over devices
    if dname not in df_data:
      continue

    df_results = df_data[dname].features          # Get the device feature data
    dc_name = get_box({'text': devices[dname] })  # First cell is the device short name
    ch_match = df_data[dname].get('ch_match',[])  # Is this a parent device?
    if ch_match:                                  # ... then we need a footnote saying "this includes these other devices"
      label_count += 1
      fn_name = f'ft{TABLE_COUNT}-{dname}'        # Get the footnote name (based on table# and device name)
      dc_name.fn.refid = fn_name
      dc_name.fn.label = f"*{label_count}"        # ... the footnote labels are numbered per-table
      fn = nodes.footnote(ids=[fn_name])          # Create a new footnote
      fn += nodes.label(text=dc_name.fn.label)    # ... add its label and "includes... " text
      fn_text = 'Includes '+', '.join([ devices[x] for x in ch_match ])
      if 'ch_mismatch' in df_data[dname]:         # ... add "does not include" text if needed
        fn_text += ', but not '+', '.join([ devices[x] for x in df_data[dname].ch_mismatch ])
      fn += nodes.paragraph(text=fn_text)         # Convert the text into a paragraph
      footnotes += [ fn ]                         # ... and save the footnote

    device_row = [ dc_name ] + df_results         # Convert device features into a device row
    device_data.append(device_row)                # ... and append it to the table list-of-lists

  return (device_data,footnotes)

def device_features(settings: Box, table_def: Box) -> typing.Tuple[typing.List[typing.List],typing.List]:
  """
  Create the device features table contents

  * Get the device data (which device supports which feature)
  * Remove child devices that inherited features from their parents
  * Remove meta devices that have no children
  * Return the list-of-lists table data structure and footnotes
  """
  df_data = get_device_features(settings,table_def)
#  for dk,dv in df_data.items():
#    print(f'{dk}: {dv}')
  remove_duplicate_features(settings,df_data)
  remove_meta_devices(settings,df_data)
  return build_device_feature_matrix(settings,df_data)

class Features(SphinxDirective):
  """Create a table with one column per feature parameter."""

  required_arguments = 0
  optional_arguments = 0
  final_argument_whitespace = True
  has_content = True

  def run(self) -> list[nodes.Node]:
    """
    Directive entry point: parse the features from directive contents and return
    the table/footnotes
    """
    global DIRECTIVE
    DIRECTIVE = self

    table_def = self._parse_features()
    (table,footnotes) = self._build_table(table_def)
#    for fn in footnotes:
#      print(fn)
    return [ table ] + footnotes

  def _parse_features(self) -> Box:
    """
    Convert directive contents into YAML and try to parse it, first as a dictionary,
    then as a list (which gets into "features" dictionary)
    """
    yaml = "\n".join(self.content)
    try:
      return Box.from_yaml(yaml_string=yaml)
    except BoxError:
      try:
        return get_box({'features': BoxList.from_yaml(yaml_string=yaml)})
      except Exception as ex:
        error = ex
    except Exception as ex:
      error = ex

    raise self.error(f"Cannot parse feature table definition as YAML: {error}")

  def _build_table(self, table_def: Box) -> typing.Tuple:
    """
    Build docutils table: create it, add header, collect device data and footnotes,
    and convert device data into a full-blown table
    """
    global SETTINGS
    (table,tgroup) = create_features_table(table_def.features)
    features_header(tgroup,table_def.features)
    (device_data,footnotes) = device_features(SETTINGS,table_def)
    features_body(tgroup,device_data)
    return (table,footnotes)

def setup(app: typing.Any) -> dict[str, object]:
  """
  Directive setup: read system defaults, move daemons into "devices" dictionary,
  process child device inheritances, and register the directive.
  """
  global SETTINGS
  topology = _read.load("package:cli/empty.yml",user_defaults=[])
  devices.merge_daemons(topology)
  devices.process_device_inheritance(topology)

  SETTINGS = topology.defaults

  app.add_directive("features", Features)
  return {
    "version": "0.1",
    "parallel_read_safe": True,
    "parallel_write_safe": True,
  }
