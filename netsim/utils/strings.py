#
# Common routines for create-topology script
#
import textwrap
from box import Box

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
  return str(eval(f"f'{fmt}'",dict(data)))                            # An awful hack to use f-string specified in a string variable
