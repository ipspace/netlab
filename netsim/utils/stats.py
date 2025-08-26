# Usage stats utility functions
#
import os
import time
import typing

from box import Box
from filelock import FileLock

from ..augment import devices
from ..data import get_box, get_empty_box
from ..data.global_vars import get_const
from ..utils import log

'''
get_filename -- get the name of the netlab stats file
'''
def get_filename() -> str:
  fname = get_const('stats_file','~/.netlab/stats.json')
  return os.path.expanduser(fname)

'''
timestamp as int
'''
def ts_int() -> int:
  return int(time.clock_gettime(time.CLOCK_REALTIME))

'''
read_stats -- read the stats file into a Box data structure
'''
def read_stats(fname: typing.Optional[str] = None) -> Box:
  fname = fname or get_filename()
  if not os.path.exists(fname):
    return get_box({'_created': ts_int() })
  try:
    return Box.from_json(filename=fname,default_box=True,box_dots=True)
  except Exception as ex:
    log.warning(
      text=f'Cannot read usage statistics file {fname}',
      more_data=str(ex),
      module='stats')
    return get_box({'_error': str(ex)})

'''
lock_stats: try to acquire the lock on the status file
'''
STAT_LOCK: typing.Any = None

def lock_stats(fname: typing.Optional[str]) -> bool:
  global STAT_LOCK
  if STAT_LOCK:
    return True
  
  lock_name = f'{fname}.lock'
  try:
    STAT_LOCK = FileLock(lock_name, timeout=3)
    STAT_LOCK.acquire()
    return True
  except Exception as ex:
    log.warning(
      text=f'Cannot lock stats file {lock_name}',
      more_data=str(ex),
      module='stats')
    STAT_LOCK = None
    return False

def unlock_stats() -> None:
  global STAT_LOCK
  if STAT_LOCK:
    STAT_LOCK.release()
    STAT_LOCK = None

'''
lock_and_read_stats: get a lock on the stats file and read it

Used as the first step in updating statistics
'''
def lock_and_read_stats() -> typing.Optional[Box]:
  stat_name = get_filename()
  try:
    status_dir = os.path.dirname(stat_name)
    if not os.path.exists(status_dir):
      os.makedirs(status_dir)
  except:
    log.fatal(f'Cannot create lab status directory {status_dir}')

  if lock_stats(stat_name):
    s_data = read_stats(stat_name)
    return s_data
  else:
    return None

'''
write_stats: recreate the stats file from in-memory data and unlock it
'''
def write_stats(stats: Box, force: bool = False) -> None:
  if stats.get('_disabled',False) and not force:
    return

  ts = ts_int()
  if '_created' not in stats:
    stats._created = ts

  if '_id' not in stats:
    stats._id = format(time.time_ns(),'020x')

  stats._updated = ts
  stat_name = get_filename()
  if lock_stats(stat_name):
    stats.to_json(filename=stat_name,indent=2)
    unlock_stats()

'''
Add value to a counter:

* Increase the absolute value of the counter
* Increase the interim counter used for averaging
'''
avg_decay = (1/2) ** (1/90)                                           # The half-time of average decay is 90 days

def add_counter(stats: Box, cnt: str, value: int = 1) -> None:
  global avg_decay
  for kw in ['cnt','avg_cnt']:                                        # Increase counters by the specified value
    if isinstance(stats[cnt][kw],int):
      stats[cnt][kw] += value
    else:                                                             # Or start from scratch
      stats[cnt][kw] = value

  ts = ts_int()
  stats[cnt].upd = ts                                                 # Also, remember when we updated the counter
  if not isinstance(stats[cnt].avg_upd,int):                          # And start averaging if needed
    stats[cnt].avg_upd = ts
  
  if stats[cnt].upd - stats[cnt].avg_upd >= 86400:                    # Update the averages at most once a day
    if not isinstance(stats[cnt].avg,float):
      stats[cnt].avg = stats[cnt].avg_cnt                             # Use current aggregate as initial average
    else:                                                             # Black magic starts here :)
      time_diff = (stats[cnt].upd - stats[cnt].avg_upd) / 86400       # ... decay time in days
      decay = avg_decay^time_diff                                     # ... and decay based on 90-day half-time

      # Update average based on calculated half-time
      stats[cnt].avg = stats[cnt].avg * decay + stats[cnt].avg_cnt * (1 - decay)
      stats[cnt].avg_upd = ts                                         # Remember when we last updated the average
      stats[cnt].avg_cnt = 0                                          # ... and clear the last-interval counter

'''
Sometimes we're using interim counters (max_vals) and and then update the
absolute maximum in statistics (for example, maximum number of devices)
'''
def update_max_vals(stats: Box, max_vals: Box) -> None:
  if 'cnt' in max_vals:
    if not isinstance(max_vals.cnt,int):
      return
    if not isinstance(stats.max,int):
      stats.max = 0
    if stats.max < max_vals.cnt:
      stats.max = max_vals.cnt
  else:
    for k in max_vals.keys():
      update_max_vals(stats[k],max_vals[k])

'''
The fun starts here: collect statistics from lab topology data
'''
def update_topo_stats(topology: Box) -> None:
  stats = lock_and_read_stats()
  if not stats:
    return

  max_vals = get_empty_box()
  add_counter(stats,f'provider.{topology.provider}.use')            # Count the use of primary provider
  p_list = [ topology.provider ]
  plugins = topology.get('plugin',[])                               # Get the list of plugins used in this topology

  for ndata in topology.nodes.values():
    n_provider = devices.get_provider(ndata,topology.defaults)      # For node-specific providers
    if n_provider not in p_list:
      add_counter(stats,f'provider.{topology.provider}.use')        # ... count the provider use (but only once)
      add_counter(stats,f'provider.{topology.provider}.secondary')  # ... and remember it was a secondary provider
      p_list.append(n_provider)

    add_counter(stats,f'device.{ndata.device}.use')                 # Count how often a device is used
    add_counter(max_vals,f'device.{ndata.device}.use')              # ... and how many devices of that type were used
    add_counter(stats,f'device.{ndata.device}.provider.{n_provider}')
    for m in ndata.get('module',[]):
      add_counter(stats,f'device.{ndata.device}.module.{m}')        # Count device/module statistics
      add_counter(max_vals,f'module.{m}.use')                       # ... and max number of devices using a module
  
    for c in ndata.get('config',[]):
      if c not in plugins:
        add_counter(stats,f'device.{ndata.device}.custom')          # Someone is using a custom config template
      else:
        c = c.replace('.','_')
        add_counter(stats,f'device.{ndata.device}.plugin.{c}')      # Count device/plugin statistics
        add_counter(max_vals,f'plugin.{c}.use')                     # ... and max devices using a plugin

  for m in topology.get('module',[]):                               # Count overall module use
    add_counter(stats,f'module.{m}.use')

  for p in plugins:                                                 # Count overall plugin use
    p = p.replace('.','_')
    add_counter(stats,f'plugin.{p}.use')

  update_max_vals(stats,max_vals)                                   # Move max values to statistics
  write_stats(stats)                                                # ... and update statistics

def stats_update_error(ex: Exception,item: str = '') -> None:
  if item:
    item = ' ' + item

  log.warning(
    text=f'Cannot update usage statistics{item}',
    more_hints=str(ex),
    module='stats')

'''
A wrapper around a bunch of other functions that increments a single counter.
Used for simple stuff like counting commands
'''
def stats_counter_update(cnt: str, val: int = 1) -> None:
  try:
    stats = lock_and_read_stats()
    if stats is None:
      unlock_stats()
      return

    add_counter(stats,cnt,val)
    write_stats(stats)
  except Exception as ex:
    stats_update_error(ex,f'counter {cnt}')

'''
Change any data in usage statistics
'''
def stats_change_data(data: typing.Union[Box,dict]) -> None:
  try:
    stats = lock_and_read_stats()
    if stats is None:
      unlock_stats()
      return

    write_stats(stats+data,force=True)
  except Exception as ex:
    stats_update_error(ex)
