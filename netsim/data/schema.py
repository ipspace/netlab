#
# Create a JSON schema for lab topologies from the attribute definitions
#
# The schema is used by editors (completion, early warnings). It describes the
# lab topology as written by the user, so it has to accept everything the data
# validation accepts: input shortcuts (node lists, link strings, dotted keys),
# values the validation functions convert (scalars into lists, strings into
# integers) and True/False replacements. The checks that need the whole lab
# topology (node names, enabled modules, valid_with) are left to 'netlab create'.
#

import copy
import json
import typing

from box import Box, BoxList

from . import get_a_list, get_box
from . import validate as _validate

SCHEMA_ID: typing.Final[str] = 'https://netlab.tools/topology.schema.json'
SCHEMA_DRAFT: typing.Final[str] = 'http://json-schema.org/draft-07/schema#'

# Python data types that can be used in the _alt_types lists
ALT_PYTHON_TYPES: typing.Final[dict] = {
  'NoneType': 'null',
  'bool': 'boolean',
  'str': 'string',
  'int': 'integer',
  'float': 'number',
  'list': 'array',
  'BoxList': 'array',
  'dict': 'object',
  'Box': 'object',
}

# Strings accepted as boolean values (see must_be_bool)
BOOL_STRINGS: typing.Final[list] = [ 'true', 'True', 'false', 'False' ]

# Alternate data types that are also checked with their validation functions, which accept strings
ALT_VALIDATED_TYPES: typing.Final[list] = [ 'bool', 'int', 'float' ]

# Data types that are validated with a False value instead of removing the attribute
FALSE_IS_VALIDATED: typing.Final[list] = [ 'bool', 'bool_false', 'ipv4', 'ipv6', 'error' ]

# IP address uses that accept integers and boolean values (see common_addr_parse)
IP_INT_USE: typing.Final[dict] = { 'ipv4': [ 'interface', 'id' ], 'ipv6': [ 'interface' ] }
IP_BOOL_USE: typing.Final[list] = [ 'interface', 'subnet_prefix' ]

# Routing objects that are normalized before validation (see modules/routing/__init__.py):
# a single entry or a list of entries, AS paths and communities can be specified as values,
# and communities can be a dictionary with the list of entries in the 'value' attribute
ROUTING_OBJECTS: typing.Final[dict] = {
  'policy': { 'entry': 'rp_entry' },
  'prefix': { 'entry': 'pfx_entry' },
  'aspath': { 'entry': 'aspath_entry', 'value': True },
  'community': { 'entry': 'community_entry', 'value': True, 'list_attr': 'value' },
  'acl': { 'entry': 'acl_entry' },
}

INT_STRING: typing.Final[str] = r'^\s*[-+]?[0-9_]+\s*$'
FLOAT_STRING: typing.Final[str] = r'^\s*[-+]?([0-9_]+(\.[0-9_]*)?|\.[0-9_]+)([eE][-+]?[0-9]+)?\s*$'

def id_pattern(max_length: typing.Any = None) -> str:
  """
  Regular expression matching an identifier (see _id_validator). The length limit is
  skipped when it's a constant that could be changed in the lab topology.
  """
  if isinstance(max_length,int) and not isinstance(max_length,bool):
    return f'^[a-zA-Z_][a-zA-Z0-9_-]{{0,{max_length - 1}}}$'
  return '^[a-zA-Z_][a-zA-Z0-9_-]*$'

def one_of_schemas(alternatives: list) -> dict:
  """
  Combine alternate schemas, skipping duplicates
  """
  unique: list = []
  for s in alternatives:
    if s not in unique:
      unique.append(s)
  return unique[0] if len(unique) == 1 else { 'anyOf': unique }

def dotted_keys(keys: typing.Iterable) -> dict:
  """
  Lab topology keys can use the dotted notation (bgp.as). We accept the dotted keys that
  start with a known attribute but don't validate their values.
  """
  names = sorted(set(k for k in keys if isinstance(k,str) and k.isidentifier()))
  return { f'^({"|".join(names)})\\.': {} } if names else {}

def object_schema(schema: dict) -> dict:
  """
  Get the dictionary alternative of a data type (for example, a dictionary that can be False)
  """
  return next(s for s in schema.get('anyOf',[ schema ]) if s.get('type',None) == 'object')

def nullable(schema: dict) -> dict:
  return one_of_schemas([ *schema.get('anyOf',[ schema ]), { 'type': 'null' } ])

def replace_refs(data: typing.Any, renamed: dict) -> typing.Any:
  if isinstance(data,dict):
    if data.get('$ref',None) in renamed:
      return { **data, '$ref': renamed[data['$ref']] }
    return { k: replace_refs(v,renamed) for k,v in data.items() }
  if isinstance(data,list):
    return [ replace_refs(v,renamed) for v in data ]
  return data

def merge_duplicates(schema: dict) -> dict:
  """
  Module attributes are often identical in different objects (for example, nodes and
  node groups). Keep a single copy of identical definitions.
  """
  while True:
    seen: dict = {}
    renamed: dict = {}
    for name in sorted(schema['definitions'],key=lambda n: (len(n),n)):
      content = json.dumps(schema['definitions'][name],sort_keys=True)
      if content in seen:
        renamed[f'#/definitions/{name}'] = f'#/definitions/{seen[content]}'
      else:
        seen[content] = name
    if not renamed:
      return schema
    for name in renamed:
      schema['definitions'].pop(name.split('/')[-1])
    schema = replace_refs(schema,renamed)

class SchemaBuilder:
  """
  Translate the attribute definitions into JSON schema definitions. Object types
  validated with validate_attributes (nodes, links, VLANs...) become shared
  definitions; other data types are translated in place.
  """
  def __init__(self, defaults: Box) -> None:
    self.defaults = defaults
    self.attributes = defaults.attributes
    self.modules = sorted(m for m in defaults.keys()
                            if isinstance(defaults[m],Box) and 'supported_on' in defaults[m])
    self.devices = sorted(defaults.devices.keys())
    self.definitions: dict = {}
    self.context: list = [ (self.attributes,'',True) ]      # Attributes, definition prefix, module attributes allowed

  def ref(self, name: str) -> dict:
    return { '$ref': f'#/definitions/{name}' }

  def const(self, name: str, default: typing.Any) -> typing.Any:
    return self.defaults.const.get(name,default)

  #
  # Schemas of individual data types (the must_be_X validation functions)
  #
  def simple_type(self, data_type: Box) -> dict:
    dt_name = data_type.get('type',None)
    use = data_type.get('use','')

    if dt_name in ('str','string'):
      return { 'type': 'string' }
    if dt_name == 'id':
      return { 'type': 'string', 'pattern': id_pattern(data_type.get('max_length',16)) }
    if dt_name in ('int','float'):
      schema: dict = {
        'type': [ 'integer' if dt_name == 'int' else 'number', 'string' ],
        'pattern': INT_STRING if dt_name == 'int' else FLOAT_STRING }
      for kw,s_kw in (('min_value','minimum'),('max_value','maximum')):
        value = data_type.get(kw,None)
        if isinstance(value,(int,float)) and not isinstance(value,bool):    # Skip limits set with constants
          schema[s_kw] = value
      return schema
    if dt_name == 'bool':
      return one_of_schemas([ { 'type': 'boolean' }, { 'enum': BOOL_STRINGS } ])
    if dt_name == 'bool_false':
      return { 'const': False }
    if dt_name == 'time':
      return { 'type': [ 'number', 'string' ], 'pattern': r'^\s*[0-9]+(\.[0-9]+)?(ms|s)\s*$' }
    if dt_name == 'asn':
      return {
        'type': [ 'integer', 'string' ], 'minimum': 0, 'maximum': 4294967295,
        'pattern': r'^[0-9]+(\.[0-9]+)?$' }
    if dt_name == 'asn2':
      return { 'type': 'integer', 'minimum': 0, 'maximum': 65535 }
    if dt_name in ('ipv4','ipv6'):
      types = [ 'string' ]
      if use in IP_INT_USE[dt_name]:
        types.append('integer')
      if use in IP_BOOL_USE:
        types.append('boolean')
      return { 'type': types[0] if len(types) == 1 else types }
    if dt_name == 'net':
      return { 'type': 'string', 'pattern': r'^[0-9a-f.]+$' }
    if dt_name == 'rd':
      return { 'type': [ 'string', 'integer', 'null' ] }
    if dt_name == 'esi_value':
      return { 'type': 'string', 'pattern': r'^00(:[0-9a-fA-F]{2}){9}$' }
    if dt_name == 'device':
      devices = self.devices
      if data_type.get('include_templates',False):
        devices = sorted(set(devices) | set(self.const('template_devices',[])))
      return { 'enum': devices }
    if dt_name == 'r_proto':
      return { 'enum': self.const('routing_protocols',[]) }
    if dt_name in ('prefix_str','named_pfx','addr_pool','node_id','group_id','node_or_group','mac','prefixset'):
      return { 'type': 'string' }
    if dt_name == 'error':
      return { 'not': {} }
    if dt_name == 'NoneType':
      return { 'type': 'null' }

    return {}                                               # Data types we don't know (for example, from plugins)

  def subtype(self, subtype: typing.Any) -> dict:
    """
    Dictionary values and list elements: an object type defined in the current attributes
    (global or module attributes) is validated like a node or a link, anything else is
    a data type (see validate_dictionary and validate_list)
    """
    if isinstance(subtype,str) and subtype in self.context[-1][0]:
      return self.object_type([ subtype ])
    return self.data_type(subtype)

  def dict_type(self, data_type: Box) -> dict:
    schema: dict = { 'type': 'object' }
    if '_keys' in data_type:
      keys = data_type._keys
      schema['properties'] = { k: self.data_type(v) for k,v in keys.items() }
      if dotted_keys(keys.keys()):
        schema['patternProperties'] = dotted_keys(keys.keys())
      schema['additionalProperties'] = False
    elif '_subtype' in data_type or '_keytype' in data_type:
      schema['patternProperties'] = { r'\.': {} }          # Values of dotted keys are not validated
    if '_subtype' in data_type:
      schema['additionalProperties'] = self.subtype(data_type._subtype)
    if '_keytype' in data_type:
      key_type = self.data_type(data_type._keytype,keys_only=True)
      schema['propertyNames'] = one_of_schemas([ key_type, { 'pattern': r'\.' } ])
    return schema

  def list_type(self, data_type: Box) -> dict:
    if '_subtype' in data_type:
      item = self.subtype(data_type._subtype)
    elif 'valid_values' in data_type:
      item = { 'enum': list(data_type.valid_values) }
    else:
      item = {}

    schema: dict = { 'type': 'array', 'items': item }
    if isinstance(data_type.get('min_length',None),int):
      schema['minItems'] = data_type.min_length
    elif data_type.get('empty',True) is False:
      schema['minItems'] = 1
    if isinstance(data_type.get('max_length',None),int):
      schema['maxItems'] = data_type.max_length

    if data_type.get('min_length',0) >= 2:                  # Scalars become single-element lists
      return schema
    if data_type.get('make_list',False):
      return one_of_schemas([ schema, {} ])
    scalar: dict = { 'type': [ 'string', 'number', 'boolean' ] }   # Only scalars become single-element lists
    if item.get('enum',None):
      scalar = item
    elif item:
      scalar = { 'allOf': [ item, scalar ] }
    return one_of_schemas([ schema, scalar ])

  def data_type(self, data_type: typing.Any, keys_only: bool = False) -> dict:
    """
    Translate a data type definition (see validate_item). keys_only is used for dictionary
    keys that are always strings.
    """
    if data_type is None:                                   # Not validated, anything goes
      return {}

    if isinstance(data_type,str) and data_type in self.attributes and not keys_only:
      name = f'{self.context[-1][1]}{data_type.lstrip("_")}_type'
      if name not in self.definitions:                      # User-defined data types become shared definitions
        self.definitions[name] = {}
        self.definitions[name] = self.data_type(self.attributes[data_type])
      return self.ref(name)

    dt = get_box(_validate.transform_validation_shortcuts(data_type))
    dt_name = dt.get('type',None)

    if dt_name == 'dict':
      schema = self.dict_type(dt)
    elif dt_name == 'list':
      schema = self.list_type(dt)
    else:
      schema = self.simple_type(dt)
      if dt_name in ('str','string') and 'valid_values' in dt:
        schema = { 'enum': list(dt.valid_values) }
    if keys_only:
      return schema

    alternatives = [ schema ]
    for alt in get_a_list(dt.get('_alt_types',[])):
      alternatives.append(self.alt_type(alt))
    if '_list_to_dict' in dt:                               # List elements become dictionary keys
      keys = list(dt.get('_keys',{}).keys())
      item = { 'enum': keys } if keys else \
             self.data_type(dt._keytype,keys_only=True) if '_keytype' in dt else { 'type': 'string' }
      alternatives.append({ 'type': 'array', 'items': item })
    if '_value_to_dict' in dt:
      alternatives.append(self.value_to_dict(dt))
    if dt.get('create_empty',False):
      alternatives.append({ 'type': 'null' })
    if 'true_value' in dt:
      alternatives.append({ 'const': True })
    if dt_name not in FALSE_IS_VALIDATED:                   # False removes the attribute or sets it to an empty value
      alternatives.append({ 'const': False })

    result = one_of_schemas(alternatives)
    if result is schema:
      result = dict(schema)
    description = dt.get('_help',None) or dt.get('_description',None) or dt.get('_err_msg',None)
    if isinstance(description,str):
      result['description'] = description.strip()
    if '_default' in dt:
      result['default'] = dt._default.to_dict() if isinstance(dt._default,Box) else \
                          dt._default.to_list() if isinstance(dt._default,BoxList) else dt._default
    return result

  def value_to_dict(self, data_type: Box) -> dict:
    """
    A non-dictionary value is copied into the keys of the _value_to_dict template that are
    set to '{value}' (see transform_value_to_dict), so it must be valid for all of them
    """
    keys = data_type.get('_keys',{})
    value_keys = [ k for k,v in data_type._value_to_dict.items() if v == '{value}' and k in keys ]
    schema: dict = { 'not': { 'type': 'object' } }
    if value_keys:
      schema = { 'allOf': [ schema ] + [ self.data_type(keys[k]) for k in value_keys ] }
    return schema

  def alt_type(self, alt: typing.Any) -> dict:
    """
    An alternate data type is checked with its validation function only (see validate_alt_type)
    """
    if isinstance(alt,str) and alt in ALT_PYTHON_TYPES and alt not in ('list','dict'):
      if alt in ALT_VALIDATED_TYPES:                        # The validation function also accepts strings
        return self.simple_type(get_box({ 'type': alt }))
      return { 'type': ALT_PYTHON_TYPES[alt] }                # 'list' and 'dict' also have validation functions
    dt = get_box(_validate.transform_validation_shortcuts(alt))
    if dt.get('type',None) == 'dict':
      return { 'type': 'object' }
    if dt.get('type',None) == 'list':
      return self.list_type(get_box({ k:v for k,v in dt.items() if k != '_subtype' }))
    return self.data_type(dt)

  #
  # Objects validated with validate_attributes: their own attributes, attributes from
  # other namespaces, and module attributes
  #
  def object_type(
        self,
        attr_list: typing.List[str],
        name: typing.Optional[str] = None,
        module: typing.Optional[str] = None,
        extra: typing.Optional[Box] = None,
        ignored: typing.List[str] = [ '_' ]) -> dict:

    if module:                                              # Module attributes, no further modules
      context = (self.defaults[module].attributes,f'{module}_',False)
    else:                                                   # Nested objects use the parent's attributes
      context = self.context[-1]
    name = context[1] + (name or '_'.join(attr_list).lstrip('_'))
    if name in self.definitions:
      return self.ref(name)
    self.definitions[name] = {}                             # Recursive object types refer to the definition

    attributes = context[0] + extra if extra else context[0]
    namespaces = _validate.get_attribute_namespaces(attributes,attr_list)
    valid = _validate.get_valid_attributes(attributes,namespaces)

    self.context.append(context)
    if isinstance(valid,str):
      self.definitions[name] = self.data_type(valid)
      self.context.pop()
      return self.ref(name)

    properties = { k: self.data_type(v) for k,v in valid.items() if not k.startswith('_') }
    if context[2]:
      for m in self.modules:
        if m not in properties:
          properties[m] = self.module_type(m,namespaces,name)
    self.context.pop()

    schema: dict = { 'type': [ 'object', 'null' ] }
    if isinstance(valid.get('_description',None),str):
      schema['description'] = valid._description.strip()
    schema['properties'] = properties
    schema['patternProperties'] = { f'^({"|".join(ignored)})': {} }
    schema['patternProperties'].update(dotted_keys(properties.keys()))
    schema['additionalProperties'] = False
    self.definitions[name] = schema
    return self.ref(name)

  def module_type(self, module: str, namespaces: list, parent: str) -> dict:
    m_attr = self.defaults[module].attributes
    alternatives = [ self.object_type(namespaces,name=parent,module=module) ]
    if _validate.validate_module_can_be_false(self.attributes,namespaces):
      alternatives.append({ 'const': False })
    if set(namespaces) & set(m_attr.get('can_be_true',[])):
      alternatives.append({ 'const': True })
    return one_of_schemas(alternatives)

  def extra_attributes(self, namespaces: typing.List[str]) -> Box:
    return _validate.get_object_attributes(namespaces,get_box({ 'defaults': self.defaults }))

  #
  # The lab topology: global attributes and the input formats of nodes, links and groups
  #
  def node_type(self) -> dict:
    node_ref = self.object_type(
      [ 'node' ],
      extra=self.extra_attributes(self.attributes.node_extra_ns),
      ignored=[ '_', 'netlab_', 'ansible_' ])
    node = self.definitions['node']
    node['properties']['loopback'] = one_of_schemas([ self.object_type([ 'loopback' ]), self.alt_type('bool') ])
    node['properties']['module'] = self.module_list()
    node['properties']['include'] = {
      'type': 'string', 'pattern': id_pattern(),
      'description': 'Topology component to include in place of this node' }
    node['properties']['image'] = { 'type': 'string', 'description': 'Container image or VM box' }
    node['properties']['group'] = self.list_type(get_box({ 'type': 'list', '_subtype': 'str' }))
    for k in ('box','group'):                               # An empty value selects the default box or no groups
      node['properties'][k] = nullable(node['properties'][k])
    return node_ref

  def node_name(self) -> dict:
    return { 'type': 'string', 'pattern': id_pattern() }

  def module_list(self) -> dict:
    return self.list_type(get_box({ 'type': 'list', 'valid_values': self.modules }))

  def nodes(self, node_ref: dict) -> dict:
    named_node = { 'allOf': [ node_ref, { 'type': 'object', 'required': [ 'name' ] } ] }
    return one_of_schemas([
      { 'type': 'object',
        'propertyNames': self.node_name(),
        'additionalProperties': one_of_schemas([ node_ref, { 'type': 'null' } ]) },
      { 'type': 'array', 'items': { 'anyOf': [ self.node_name(), named_node ] } },
      { 'type': 'null' } ])

  def links(self) -> dict:
    extra = self.extra_attributes([ 'providers', 'outputs' ])
    intf_ref = self.object_type([ 'interface', 'link' ],name='interface',extra=extra)
    link_ref = self.object_type([ 'link' ],extra=extra)

    link = self.definitions['link']                         # Node names can be used as keys in a link dictionary
    link['properties']['interfaces'] = one_of_schemas([     # A single node name becomes a list (adjust_link_object)
      { 'type': 'array', 'items': { 'anyOf': [ self.node_name(), intf_ref ] } },
      self.node_name() ])
    link['additionalProperties'] = one_of_schemas([ intf_ref, { 'type': 'null' } ])
    link['patternProperties'][r'\.'] = {}                   # ... including dotted keys (r1.ospf.cost)

    self.definitions['link_list'] = one_of_schemas([
      { 'type': 'array',
        'items': { 'anyOf': [
          { 'type': 'string' },
          { 'type': 'array', 'items': { 'anyOf': [ self.node_name(), intf_ref ] } },
          link_ref ] } },
      { 'type': 'object', 'additionalProperties': self.ref('link_list') },    # Link groups
      { 'type': 'string' },
      { 'type': 'null' } ])
    return self.ref('link_list')

  def groups(self) -> dict:
    extra = self.extra_attributes(self.attributes.node_extra_ns)
    ignored = [ '_', 'netlab_', 'ansible_' ]
    node_group = self.object_type([ 'node_group' ],extra=extra,ignored=ignored)
    vlan_group = self.object_type([ 'vlan_group' ],extra=extra,ignored=ignored)
    vrf_group = self.object_type([ 'vrf_group' ],extra=extra,ignored=ignored)
    self.definitions['node_group']['properties']['module'] = self.module_list()
    for g_def in ('node_group','vlan_group','vrf_group'):   # Members could be regular expressions or wildcards
      self.definitions[g_def]['properties']['members'] = self.list_type(get_box({ 'type': 'list', '_subtype': 'str' }))

    def group_type(g_type: str) -> dict:
      return { 'properties': { 'type': { 'const': g_type } }, 'required': [ 'type' ] }

    group = {
      'if': group_type('vlan'),
      'then': vlan_group,
      'else': { 'if': group_type('vrf'), 'then': vrf_group, 'else': node_group } }
    return {
      'type': 'object',
      'propertyNames': one_of_schemas([ self.node_name(), { 'pattern': '^_' } ]),
      'patternProperties': { '^_': {} },
      'additionalProperties': one_of_schemas([
        { 'type': 'array', 'items': { 'type': 'string' } },
        group ]) }

  def components(self, node_ref: dict, links: dict) -> dict:
    component = copy.deepcopy(self.definitions['node'])
    component['properties']['nodes'] = self.nodes(node_ref)
    component['properties']['links'] = links
    component['patternProperties'].update(dotted_keys([ 'nodes', 'links' ]))
    component.pop('required',None)
    self.definitions['component'] = component
    return {
      'type': 'object',
      'propertyNames': self.node_name(),
      'additionalProperties': self.ref('component') }

  def routing_shortcuts(self) -> None:
    """
    Routing objects can be a list of entries, a single entry, or (AS paths, communities)
    a value or a list of values. Policy entries can use 'set' and 'match' keywords directly.
    """
    shortcuts = self.defaults.routing.attributes.get('route_map',{})
    self.context.append((self.defaults.routing.attributes,'routing_',False))
    for d_name,d_value in list(self.definitions.items()):
      if not d_name.startswith('routing_') or 'properties' not in d_value:
        continue
      for o_type,o_def in ROUTING_OBJECTS.items():
        if o_type not in d_value['properties']:
          continue
        entry = self.data_type(o_def['entry'])
        if o_type == 'policy':
          entry = self.policy_shortcuts(entry,shortcuts)
        items = [ entry, { 'type': [ 'string', 'number', 'array' ] } ] if o_def.get('value',False) else [ entry ]
        o_list = { 'type': 'array', 'items': one_of_schemas(items) }
        alternatives = [ o_list, *items ]
        if 'list_attr' in o_def:                            # A dictionary with the list of entries
          o_dict = object_schema(d_value['properties'][o_type])['additionalProperties']
          o_dict = copy.deepcopy(object_schema(o_dict))
          o_dict['properties'][o_def['list_attr']] = o_list
          o_dict['required'] = [ o_def['list_attr'] ]
          alternatives.append(o_dict)
        o_value = one_of_schemas([ *alternatives, { 'type': 'null' } ])
        d_value['properties'][o_type] = one_of_schemas([
          { 'type': 'object',
            'patternProperties': { r'\.': {} },
            'additionalProperties': o_value },
          { 'const': False } ])
    self.context.pop()

  def policy_shortcuts(self, entry: dict, shortcuts: Box) -> dict:
    name = entry['$ref'].split('/')[-1] + '_shortcuts'
    if name not in self.definitions:
      p_entry = copy.deepcopy(self.definitions[entry['$ref'].split('/')[-1]])
      p_props = object_schema(p_entry)['properties']
      self.policy_values(p_props)
      for kw in ('set','match'):
        for k in shortcuts.get(kw,[]):
          p_props[k] = object_schema(p_props[kw])['properties'][k]
      object_schema(p_entry)['patternProperties'] = dotted_keys(p_props.keys())
      self.definitions[name] = p_entry
    return self.ref(name)

  def policy_values(self, p_props: dict) -> None:
    """
    Policy entry values that normalize_policy_entry turns into dictionaries: AS path prepending
    and community lists
    """
    def add_value(o_props: dict, key: str, value: dict) -> None:
      o_props[key] = one_of_schemas([ *o_props[key].get('anyOf',[ o_props[key] ]), value ])

    add_value(object_schema(p_props['set'])['properties'],'prepend',{ 'type': [ 'integer', 'string' ] })
    add_value(object_schema(p_props['match'])['properties'],'community',{ 'type': 'string' })
    d_community = object_schema(object_schema(p_props['delete'])['properties']['community'])
    add_value(d_community['properties'],'list',{ 'type': 'string' })

  def topology(self) -> dict:
    node_ref = self.node_type()                             # Nodes and links first, other objects could refer to them
    links = self.links()
    self.object_type(
      [ 'global' ],
      name='topology',
      extra=self.extra_attributes(self.attributes.global_extra_ns))
    topology = self.definitions.pop('topology')
    properties = topology['properties']

    properties['nodes'] = self.nodes(node_ref)
    properties['links'] = links
    properties['groups'] = self.groups()
    properties['components'] = self.components(node_ref,links)
    properties['module'] = self.module_list()
    properties['provider'] = { 'enum': sorted(self.defaults.providers.keys()) }
    properties['addressing']['additionalProperties'] = one_of_schemas([
      self.object_type([ 'pool' ]),
      { 'type': 'string' },                                 # An IPv4 prefix (setup_pools)
      { 'const': False } ])
    properties['addressing']['patternProperties'] = { r'\.': {} }
    pool = self.definitions['pool']['properties']
    for k in pool:                                          # An empty value removes a default pool setting
      pool[k] = nullable(pool[k])
    self.routing_shortcuts()
    properties['defaults'] = { 'type': 'object', 'description': 'Changes to system defaults' }
    properties['message'] = { 'type': 'string', 'description': 'Message displayed after the lab has started' }
    topology['patternProperties'].update(dotted_keys(properties.keys()))

    return {
      '$schema': SCHEMA_DRAFT,
      '$id': SCHEMA_ID,
      'title': 'netlab lab topology',
      'type': 'object',
      'properties': properties,
      'patternProperties': topology['patternProperties'],
      'additionalProperties': False,
      'definitions': dict(sorted(self.definitions.items())) }

def topology_schema(defaults: Box) -> dict:
  """
  Build the lab topology JSON schema from system defaults (after transform_setup
  initialized the validation code)
  """
  return merge_duplicates(SchemaBuilder(defaults).topology())
