#
# Common routines for create-topology script
#
import textwrap
import typing
from box import Box,BoxList

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

def extra_data_printout(s : str, width: int = 70) -> str:
  lines = []
  for line in s.split('\n'):
    lines.append(textwrap.TextWrapper(
      initial_indent="... ",
      subsequent_indent="      ",
      width=width).fill(line))

  return "\n".join(lines)

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
  fmt = fmt.replace("'","\\'")                    # Escape single quotes to prevent eval crashes
  return str(eval(f"f'{fmt}'",dict(data)))        # An awful hack to use f-string specified in a string variable

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

  col_len: typing.List[int] = []

  def print_row(separator: str, row: typing.Optional[list] = None, char: str = ' ') -> None:
    line = separator
    for idx,clen in enumerate(col_len):
      if row:
        value = ' ' + row[idx] + (' ' * 80)
      else:
        value = char * (clen + 2)
      line = line + value[:clen+2] + separator
    print(line)

  for idx,data in enumerate(heading):
    slice_len = [ len(k[idx]) for k in rows ]
    slice_len.append(len(heading[idx]))
    col_len.append(max(slice_len))

  print_row('+',char='-')
  print_row('|',row=heading)
  print_row('+',char='=')
  for idx,row in enumerate(rows):
    print_row('|',row=row)
    if inter_row_line:                                                # If we're printing inter-row lines...
      print_row('+',char='-')                                         # ... print one after each row

  if not inter_row_line:                                              # No inter-row lines?
      print_row('+',char='-')                                         # ... we still need one to wrap up the table
