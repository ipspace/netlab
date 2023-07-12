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
