#
# Common routines for create-topology script
#
import textwrap
import typing
from box import Box,BoxList
import rich.console, rich.table, rich.json, rich.syntax

rich_console = rich.console.Console()
rich_stderr  = rich.console.Console(stderr=True)
rich_color   = rich_console.color_system is not None

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

def extra_data_printout(s : str, width: int = 70) -> str:
  lines = []
  for line in s.split('\n'):
    lines.append(textwrap.TextWrapper(
      initial_indent="... ",
      subsequent_indent="      ",
      width=width).fill(line))

  return "\n".join(lines)

def pad_text(t: str, w: int = 10) -> str:
  return (t + " " * w)[0:w]

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

#
# eval_format: emulate f'strings' evaluated on a data structure
#
def eval_format(fmt: str, data: dict) -> str:
  fmt = fmt.replace("'","\\'")         # Escape single quotes to prevent eval crashes
  ex = "f'"+fmt+"'"                    # String to format-evaluate
  return str(eval(ex,dict(data)))      # An awful hack to use f-string specified in a string variable

"""
confirm: print the prompt and wait for a yes/no answer
"""
def confirm(prompt: str) -> bool:
  prompt = f'{prompt} [y/n]'

  while True:
    answer = input(prompt).lower()
    if answer in ['y','yes']:
      return True
    if answer in ['n','no']:
      return False

"""
print text table
"""
def print_table(
      heading: typing.List[str],
      rows: typing.List[typing.List[str]],
      inter_row_line: bool = True) -> None:

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

  rich_console.print(table)

"""
colored_text: Print colored text using rich library
"""
def print_colored_text(txt: str, color: str, stderr: bool = False) -> None:
  global rich_console, rich_stderr
  c = rich_stderr if stderr else rich_console
  txt = txt.replace('[','\\[')             # Quote square brackets so they're not treated as markup
  r_txt = f'[{color}]{txt}[/{color}]'     # Compose colored text markup
  c.print(r_txt,end='',highlight=False)
