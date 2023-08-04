#
# Dynamic output framework
# 
# Individual output routines are defined in modules within this directory inheriting
# TopologyOutput class and replacing or augmenting its methods (most commonly, write)
#

import typing
import re

# Related modules
from box import Box

from ..utils import status,log
from ..utils.callback import Callback

'''
check_writeable -- check if the current directory is writeable (does not have netlab.lock file)

Print an error message explaining what to do next and exit with a fatal error if the directory is locked
'''
def check_writeable(target: str) -> None:
  if status.is_directory_locked():
    print(f'''
It looks like you have another lab running in this directory. netlab cannot
create {target} as that might impact your ability to shut down
the other lab.

Please use 'netlab status' to check the status of labs running on this machine, or
'netlab down' to shut down the other lab running in this directory.

If you are sure that no other lab is running in this directory, you can remove
the netlab.lock file manually and retry.
''')
    log.fatal('Cannot create configuration files in a locked directory')

class _TopologyOutput(Callback):
  def __init__(self, output: str, data: Box) -> None:
    self.settings = data

    output_parts = output.split('=')

    output_list = output_parts[0].split(':')
    self.output = output_list[0]
    self.format = output_list[1:]

    if len(output_parts) > 1:
      self.filenames = output_parts[1].split(',')

  @classmethod
  def load(self, output: str, data: Box) -> typing.Optional['_TopologyOutput']:
    module_name = __name__+"."+re.split(':|=',output)[0]
    obj = self.find_class(module_name)
    if obj:
      return obj(output,data)
    else:
      return None

  def get_template_path(self) -> str:
    fmtname = self.format[0] if self.format else "default"
    return 'templates/outputs/' + self.output + "/" + fmtname + ".j2"

  def get_output_name(self, fname: str, topology: Box) -> typing.Optional[str]:
    if fname:
      return fname

    if self.settings:
      return self.settings.filename

    return None

  def write(self, topology: Box) -> None:
    log.fatal('someone called the "write" method of TopologyOutput abstract class')
