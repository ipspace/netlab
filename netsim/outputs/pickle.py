#
# Create Pickle snapshot of transformed topology
#
import pickle

from box import Box

from .. import __version__
from ..augment import topology
from ..utils import log
from . import _TopologyOutput


class YAML(_TopologyOutput):

  DESCRIPTION :str = 'Create Pickle snapshot of transformed topology'

  def write(self, topo: Box) -> None:
    outfile = self.select_output_file('netlab.snapshot.pickle',writeable=True)
    if outfile is None:
      return

    if outfile == '-':
      log.fatal('Cannot write pickled data to stdout',module='pickle')

    topodict = topology.cleanup_topology(topo).to_dict()
    topodict['_netlab_version'] = __version__
    try:
      output = open(outfile,mode='wb')
    except Exception as ex:
      log.fatal(f'Cannot open file {outfile} for writing: {str(ex)}',module='pickle')

    try:
      pickle.dump(topodict,output)
      output.close()
    except Exception as ex:
      log.fatal(f'Cannot write pickled data to {outfile}: {str(ex)}',module='pickle')

    log.status_created()
    print(f"pickled transformed topology data into {outfile}")
