"""
Sphinx extension implementing the *features* directive.

The directive takes a comma-separated list of ``feature=header`` parameters.
Each parameter defines one column of a table: *feature* is the machine-readable
feature name used by the code populating the table body, *header* is the
human-readable column header.

Usage::

    .. features:: vlan=VLAN support, vrf=VRF support, mpls=MPLS support
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

def table_cell(
      text: str,
      align: str = '',
      fn: typing.Optional[Box] = None) -> nodes.entry:
  entry = nodes.entry()
  if align:
    entry['classes'].append('text-'+align)
  para_list = []
  for line in text.split('<br>'):
    paragraph = nodes.paragraph()
    paragraph += nested_parse_to_nodes(DIRECTIVE.state,line,offset=DIRECTIVE.content_offset)
    para_list += paragraph
  if fn:
    para_list[-1] += nodes.footnote_reference(text=fn.label,refid=fn.refid)
  entry += para_list
  return entry

def features_columns(tgroup: nodes.tgroup, features: dict) -> None:
  for _ in range(len(features)+1):
    tgroup += nodes.colspec(colwidth=1)

def create_features_table(features: dict) -> typing.Tuple[nodes.table,nodes.tgroup]:
  table = nodes.table()
  tgroup = nodes.tgroup(cols=len(features) + 1)
  table += tgroup
  features_columns(tgroup,features)
  return (table,tgroup)

def features_header(tgroup: nodes.tgroup, features: BoxList) -> None:
  thead = nodes.thead()
  tgroup += thead
  header_row = nodes.row()
  thead += header_row
  header_row += table_cell('Device')
  for header in features:
    header_row += table_cell(header.get('title','???'),align="center")

def features_body(tgroup: nodes.tgroup, device_data: typing.List[typing.List]) -> None:
  tbody = nodes.tbody()
  tgroup += tbody

  for d_row in device_data:
    trow = nodes.row()
    tbody += trow
    for d_data in d_row:
      if 'text' in d_data:
        trow += table_cell(d_data['text'],fn=d_data.get('fn',''))
      elif 'status' in d_data:
        txt = '✅' if d_data['status'] else '❌'
        if 'caveat' in d_data:
          txt += f'[❗]({d_data["caveat"]})'
        trow += table_cell(txt,align='center')
      else:
        trow += table_cell('🤦‍♂️')    

def get_feature_list(settings: Box, table_def: Box) -> Box:
  df_data = get_empty_box()

  for dname,ddata in settings.devices.items():
    df_row = []
    f_valid = False
    local_data = ddata + ddata.features
    for f_def in table_def.features:
      try:
        f_OK = bool(eval(f_def.enabled,locals=local_data))
      except Exception:
        f_OK = False
      dt_value = {'status': f_OK}
      if f_OK and 'caveats' in f_def:
        try:
          f_caveat = eval(f_def.caveats,locals=local_data)
          dt_value['caveat'] = 'caveats-'+dname if f_caveat is True else f_caveat
        except Exception:
          pass
      df_row.append(dt_value)
      f_valid = f_valid or f_OK

    if f_valid:
      df_data[dname].features = df_row

  return df_data

def remove_duplicate_features(settings: Box, df_data: Box) -> None:
  for dname in list(df_data.keys()):
    ddata = settings.devices[dname]
    p_list = ddata.get('_parents',[])
    if not p_list:
      continue
    parent = p_list[0]
    if parent not in df_data:
      continue
    if not settings.devices[parent].get('docparent',True):
      continue
    if df_data[dname].features == df_data[parent].features:
      df_data.pop(dname)
      append_to_list(df_data[parent],'ch_match',dname)
    else:
      append_to_list(df_data[parent],'ch_mismatch',dname)

def remove_meta_devices(settings: Box,df_data: Box) -> None:
  for dname in list(df_data.keys()):
    ddata = settings.devices[dname]
    if not ddata.get('_meta_device',False):
      continue
    if 'ch_match' in df_data[dname]:
      continue
    df_data.pop(dname)

def build_device_feature_matrix(
      settings: Box,
      df_data: Box) -> typing.Tuple[typing.List[typing.List],typing.List]:

  global TABLE_COUNT
  TABLE_COUNT += 1

  device_data: list = []
  footnotes:   list = []

  dev_data = settings.devices
  devices = { dname: dev_data[dname].get('docname',dev_data[dname].get('description',dname)) 
                for dname in dev_data }

  label_count = 0
  for dname in sorted(devices,key=devices.get):         # type: ignore # (and feel free to fix it)
    if dname not in df_data:
      continue

    df_results = df_data[dname].features
    dc_name = get_box({'text': devices[dname] })
    ch_match = df_data[dname].get('ch_match',[])
    if ch_match:
      label_count += 1
      fn_name = f'ft{TABLE_COUNT}-{dname}'
      dc_name.fn.refid = fn_name
      dc_name.fn.label = f"*{label_count}"
      fn = nodes.footnote(ids=[fn_name])
      fn += nodes.label(text=dc_name.fn.label)
      fn_text = 'Includes '+', '.join([ devices[x] for x in ch_match ])
      if 'ch_mismatch' in df_data[dname]:
        fn_text += ', but not '+', '.join([ devices[x] for x in df_data[dname].ch_mismatch ])
      fn += nodes.paragraph(text=fn_text)
      footnotes += [ fn ]

    device_row = [ dc_name ] + df_results
    device_data.append(device_row)

  return (device_data,footnotes)

def device_features(settings: Box, table_def: Box) -> typing.Tuple[typing.List[typing.List],typing.List]:
  df_data = get_feature_list(settings,table_def)
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
    global DIRECTIVE
    DIRECTIVE = self

    table_def = self._parse_features()
    (table,footnotes) = self._build_table(table_def)
#    for fn in footnotes:
#      print(fn)
    return [ table ] + footnotes

  def _parse_features(self) -> Box:
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

  def _build_table(self, table_def: Box) -> nodes.table:
    global SETTINGS
    (table,tgroup) = create_features_table(table_def.features)
    features_header(tgroup,table_def.features)
    (device_data,footnotes) = device_features(SETTINGS,table_def)
    features_body(tgroup,device_data)
    return (table,footnotes)

def setup(app: typing.Any) -> dict[str, object]:
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
