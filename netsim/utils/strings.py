#
# Common routines for create-topology script
#
import re
import sys
import textwrap
import typing

import rich.console
import rich.json
import rich.syntax
import rich.table
from box import Box, BoxList

rich_console   = rich.console.Console()
rich_stderr    = rich.console.Console(stderr=True)
rich_color     = rich_console.color_system is not None
rich_err_color = rich_stderr.color_system is not None
rich_width     = rich_console.size.width if rich_color else 80
rich_err_width = rich_stderr.size.width if rich_err_color else 80

ruamel_attrs: typing.Final[dict] = {'version': (1,1)}

def get_yaml_string(x : typing.Any) -> str:
  global ruamel_attrs
  if isinstance(x, Box) or isinstance(x,BoxList):
    return x.to_yaml(ruamel_attrs=ruamel_attrs)
  if isinstance(x,dict):
    return Box(x).to_yaml(ruamel_attrs=ruamel_attrs)
  elif isinstance(x,list):
    return BoxList(x).to_yaml(ruamel_attrs=ruamel_attrs)
  else:
    return str(x)

def pretty_print(txt: str, fmt: str) -> None:
  if fmt == 'str':
    rich_console.out(txt)
  elif fmt == 'json':
    rich_console.print_json(txt)
  else:
    try:
      s_markup = rich.syntax.Syntax(txt,fmt)
      rich_console.print(s_markup)
    except:
      rich_console.out(txt)

"""
Given a string, split it into lines, and wrap each line to specified width.
Use custom lead-in for first and subsequent lines (default: none).
"""
def wrap_text_into_lines(
      s : str,
      width: int = 90,
      first_line: str = '',
      next_line: str = '') -> list:
  lines = []
  for line in s.split('\n'):
    wrap_line = textwrap.TextWrapper(
      initial_indent=first_line,
      subsequent_indent=next_line,
      width=width).fill(line)
    first_line = next_line
    lines.extend(wrap_line.split('\n'))
  
  return lines

def wrap_error_message(err: str, indent: int) -> str:
  global rich_err_width
  return "\n".join(wrap_text_into_lines(
    err,
    width=min(rich_err_width - indent,100),
    first_line='',
    next_line = ' ' * indent))

"""
Given a string, generate the traditional "extra data" printout:

* Text is wrapped to specified width
* First line is prepended with ..., others with four spaces to
  keep alignment
"""
def extra_data_printout(
      s : str,
      width: int = 70,
      first_line: str = '... ',
      next_line: str = '    ') -> str:
  lines = wrap_text_into_lines(s,width,first_line,next_line)
  return "\n".join(lines)

"""
Implement removeprefix for Python 3.8
"""
def removeprefix(s: str, pfx: str) -> str:
  return s[len(pfx):] if s.startswith(pfx) else s

"""
Pad text to specified width
"""
def pad_text(t: str, w: int = 10) -> str:
  return (t + " " * w)[0:w]

"""
Generate error label of specified width (default: 10)
"""
def pad_err_code(t: str, w: int = 10) -> str:
  return pad_text(f"[{t}]",w)

def format_structured_dict(d: Box, prefix: str = '') -> str:
  lines = []
  for k,v in d.items():
    if v and (isinstance(v,dict) or isinstance(v,list)):
      lines.append(f'{prefix}{k}:')
      lines.append(f'{prefix}  {v}')
    else:
      lines.append(f'{prefix}{k}: {v}')

  return "\n".join(lines)

def print_structured_dict(d: Box, prefix: str = '') -> None:
  print(format_structured_dict(d,prefix))

def string_to_list(txt: typing.Union[str,list], sep: str = ' ') -> list:
  if isinstance(txt,list):
    return txt
  
  return [ frag for frag in txt.split(sep) if frag != '' ]

"""
eval_format: emulate f'strings' evaluated on a data structure
"""
def eval_format(fmt: str, data: dict) -> str:
  fmt = fmt.replace("'","\\'")         # Escape single quotes to prevent eval crashes
  ex = "f'"+fmt+"'"                    # String to format-evaluate
  return str(eval(ex,dict(data)))      # An awful hack to use f-string specified in a string variable

def eval_format_args(fmt: str, **kwargs: typing.Any) -> str:
  return eval_format(fmt,kwargs)

"""
eval_format_list: execute eval_format on a list
"""
def eval_format_list(fmt_list: list, data: dict) -> list:
  return [ eval_format(fm_elem,data) if '{' in fm_elem else fm_elem for fm_elem in fmt_list ]

"""
confirm: print the prompt and wait for a yes/no answer
"""
def confirm(prompt: str,blank_line: bool = False) -> bool:
  if blank_line:
    print()

  prompt = f'{prompt} [y/n]: '

  try:
    while True:
      answer = input(prompt).lower()
      if answer in ['y','yes']:
        return True
      if answer in ['n','no']:
        return False
  except KeyboardInterrupt:
    from . import log
    print()
    log.fatal('Aborted by user')

"""
print text table

    heading:        list of headings
    rows:           list of row values. Each row value has N columns
    inter_row_line: do we want to have lines between individual rows?
    markup:         do cells contain Rich markup?

The default Rich behavior is to interpret cell values as having Rich markup,
which works well unless you print YAML stuff that can contain things like [b].
The 'markup' parameter was added to solve #2698; the default value is "we want
markup" just in case some other caller expects the default Rich behavior.
"""
def print_table(
      heading: typing.List[str],
      rows: typing.List[typing.List[str]],
      inter_row_line: bool = True,
      markup: bool = True) -> None:

  global rich_console

  # We're dynamically building table parameters in case we want to
  # add table title sometime in the future
  #
  t_args = {
    'show_lines': inter_row_line,
    'safe_box':   rich_console.color_system is None
  }

  # Unfortunately, mypy can't figure out that what we're doing
  # is not broken
  #
  table  = rich.table.Table(**t_args)           # type: ignore

  for h in heading:
    table.add_column(h)

  for r in rows:
    table.add_row(*r)

  rich_console.print(table,markup=markup)

"""
colored_text: Print colored text using rich library
"""
def print_colored_text(txt: str, color: str, alt_txt: typing.Optional[str] = '', stderr: bool = False) -> None:
  global rich_console, rich_stderr, rich_color, rich_err_color
  console   = rich_stderr if stderr else rich_console
  has_color = rich_err_color if stderr else rich_color

  if has_color:
    txt = txt.replace('[','\\[')             # Quote square brackets so they're not treated as markup
    r_txt = f'[{color}]{txt}[/{color}]'      # Compose colored text markup
    console.print(r_txt,end='',highlight=False)
  else:
    if alt_txt is not None:
      alt_txt = alt_txt or txt
      print(alt_txt,end='',file=sys.stderr if stderr else sys.stdout)

"""
make_id: Make an identifier out of a string
"""
def make_id(txt: str) -> str:
  not_allowed = f'[^a-zA-Z0-9_]'                        # Everything but letters, numbers, and undescore is forbidden
  id = re.sub(not_allowed,'_',txt)                      # Replace forbidden characters with underscores
  id = re.sub('^[0-9]*','',id)                          # Remove leading numbers
  if id.startswith('_') and not txt.startswith('_'):    # Remove leading underscores but only if the original text did not start
    id = re.sub('^_*','',id) or id                      # with underscores and if there's something else in the id

  return id
