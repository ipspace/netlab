#
# Dynamic virtualization provider framework
#
# Individual virtualization providers are defined in modules within this directory inheriting
# Provider class and replacing or augmenting its methods (most commonly, transform)
#

import ipaddress
import multiprocessing
import os
import pathlib
import platform
import threading
import time
import typing
from queue import Empty, Queue

# Related modules
from box import Box

from ..augment import devices, links
from ..data import append_to_list, filemaps, get_box, get_empty_box
from ..outputs.ansible import get_host_addresses
from ..utils import files as _files
from ..utils import log, strings, templates
from ..utils.callback import Callback


def get_cpu_model() -> str:
  processor_name = ""
  if platform.system() == "Windows":
    processor_name = platform.processor()
  elif platform.system() == "Darwin":
    processor_name = "arm64"          # Assume Apple silicon for MacOS
  elif platform.system() == "Linux":
    processor_name = pathlib.Path("/proc/cpuinfo").read_text().splitlines()[1].split()[2]
  return processor_name.lower()

def _progress_monitor_lightweight(progress_queue: Queue, total_tasks: int, description: str = "Processing"):
  """Ultra-lightweight progress monitor with minimal overhead"""
  completed = 0
  start_time = time.monotonic()  # Use monotonic for more accurate timing
  last_update = start_time
  update_interval = 5.0  # Update every 5 second
  
  while completed < total_tasks:
    try:
      # Non-blocking check with longer timeout to reduce overhead
      increment = progress_queue.get(timeout=1.0)
      completed += increment
      current_time = time.monotonic()
      
      # Update less frequently to reduce overhead
      if current_time - last_update > update_interval or completed == total_tasks:
        elapsed = current_time - start_time
        if completed > 0 and elapsed > 0:
          rate = completed / elapsed
          eta = (total_tasks - completed) / rate if rate > 0 else 0
          
          strings.print_colored_text('[PROGRESS]','bright_blue','')
          print(f"{description}: {completed}/{total_tasks} ({completed/total_tasks*100:.0f}%) "
                f"ETA: {eta:.0f}s")
        last_update = current_time
        
    except Empty:
      continue  # Timeout, check again
    except:
      break  # Error or queue closed

"""
The generic provider class. Used as a super class of all other providers
"""
class _Provider(Callback):
  def __init__(self, provider: str, data: Box) -> None:
    self.provider = provider
    if 'template' in data:
      self._default_template_name = data.template

  @classmethod
  def load(self, provider: str, data: Box) -> '_Provider':
    module_name = __name__+"."+provider
    obj = self.find_class(module_name)
    if obj:
      return obj(provider,data)
    else:
      return _Provider(provider,data)

  def get_template_path(self) -> str:
    return 'templates/provider/' + self.provider

  def get_full_template_path(self) -> str:
    return str(_files.get_moddir()) + '/' + self.get_template_path()

  def find_extra_template(self, node: Box, fname: str, topology: Box) -> typing.Optional[str]:
    if fname in node.get('config',[]):                    # Are we dealing with extra-config template?
      path_prefix = topology.defaults.paths.custom.dirs
      path_suffix = [ fname ]
      fname = node.device
    else:
      path_suffix = [ node.device ]
      path_prefix = topology.defaults.paths.templates.dirs + [ self.get_full_template_path() ]

      if node.get('_daemon',False):
        if '_daemon_parent' in node:
          path_suffix.append(node._daemon_parent)
        path_prefix.append(str(_files.get_moddir() / 'daemons'))

    path = [ pf + "/" + sf for pf in path_prefix for sf in path_suffix ]
    if log.debug_active('clab'):
      print(f'Searching for {fname}.j2 in {path}')

    found_file = _files.find_file(fname+'.j2',path)
    if log.debug_active('clab'):
      print(f'Found file: {found_file}')

    return found_file

  def get_output_name(self, fname: typing.Optional[str], topology: Box) -> str:
    if fname:
      return fname

    fname = topology.defaults.providers[self.provider].config
    if fname:
      return fname

    return "Vagrantfile"

  _default_template_name = "Vagrantfile.j2"

  def get_root_template(self) -> str:
    return self._default_template_name

  def node_image_version(self, topology: Box) -> None:
    for name,n in topology.nodes.items():
      if '.' in n.box:
        image_spec = n.box.split(':')
        n.box = image_spec[0]
        if len(image_spec) > 1:
          n.box_version = image_spec[1]

  def transform_node_images(self, topology: Box) -> None:
    pass

  def validate_node_image(self, node: Box, topology: Box) -> None:
    pass

  def transform(self, topology: Box) -> None:
    self.transform_node_images(topology)
    if "processor" in topology.defaults:
      return
    else:
      topology.defaults.processor = get_cpu_model()

  def create_extra_files_mappings(
      self,
      node: Box,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds') -> None:

    mappings = node.get(f'{self.provider}.{inkey}',None)
    if not mappings:
      return
    
    map_dict = filemaps.mapping_to_dict(mappings)
    cur_binds = node.get(f'{self.provider}.{outkey}',[])
    bind_dict = filemaps.mapping_to_dict(cur_binds)
    for file,mapping in map_dict.items():
      file = file.replace('@','.')
      if file in bind_dict:
        continue
      if not self.find_extra_template(node,file,topology):
        log.error(
          f"Cannot find template {file}.j2 for extra file {self.provider}.{inkey}.{file} on node {node.name}",
          category=log.IncorrectValue,
          module=self.provider)
        continue

      out_folder = f"{self.provider}_files/{node.name}"
      bind_dict[f"{out_folder}/{file}"] = mapping         # note: node_files directory is flat

    node[self.provider][outkey] = filemaps.dict_to_mapping(bind_dict)

  def create_extra_files(
      self,
      node: Box,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds') -> None:

    binds = node.get(f'{self.provider}.{outkey}',None)
    if not binds:
      return

    # Pre-compute shared data once to avoid O(n²) complexity
    shared_data = {
      'hostvars': topology.nodes,
      'hosts': get_host_addresses(topology),
      'addressing': topology.addressing
    }

    sys_folder = str(_files.get_moddir())+"/"
    out_folder = f"{self.provider}_files/{node.name}"

    bind_dict = filemaps.mapping_to_dict(binds)
    for file,mapping in bind_dict.items():
      if not out_folder in file:                  # Skip files that are not mapped into the temporary provider folder
        continue
      file_name = file.replace(out_folder+"/","")
      template_name = self.find_extra_template(node,file_name,topology)
      if template_name:
        # Create node-specific data efficiently by merging with pre-computed shared data
        node_data = {**shared_data, **node}
        if '/' in file_name:                      # Create subdirectory in out_folder if needed
          pathlib.Path(f"{out_folder}/{os.path.dirname(file_name)}").mkdir(parents=True,exist_ok=True)
        try:
          templates.write_template(
            in_folder=os.path.dirname(template_name),
            j2=os.path.basename(template_name),
            data=node_data.to_dict(),
            out_folder=out_folder, filename=file_name)
        except Exception as ex:
          log.fatal(
            text=f"Error rendering {template_name} into {file_name}\n{strings.extra_data_printout(str(ex))}",
            module=self.provider)

        strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
        print(f"{out_folder}/{file_name} to {node.name}:{mapping} (from {template_name.replace(sys_folder,'')})")
      else:
        log.error(f"Cannot find template for {file_name} on node {node.name}",log.MissingValue,'provider')

  def create_extra_files_batch(
      self,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds',
    ) -> None:
    """
    Batch process extra files for all nodes to avoid O(n²) complexity.
    This method pre-computes shared data once and processes all nodes efficiently.
    OPTIMIZED PROGRESS TRACKING - set show_progress=False for maximum performance!
    
    Args:
        topology: The topology data
        inkey: Input key for config templates
        outkey: Output key for binds
    """
    start_time = time.monotonic()
    
    # If not specified, let the smart detection decide
    use_multiprocessing = topology.defaults.providers.clab.get('use_multiprocessing', None)
    show_progress = hasattr(topology.defaults, 'show_progress')

    
    # Pre-compute shared data once for all nodes
    shared_data = {
      'hostvars': topology.nodes,
      'hosts': get_host_addresses(topology),
      'addressing': topology.addressing
    }
    
    # Pre-load and cache templates to avoid repeated file I/O
    template_cache = {}
    
    # Collect all file mappings that need processing
    file_tasks = self._collect_file_tasks(topology, inkey, outkey, template_cache)
    
    if not file_tasks:
      return
    
    # Smart multiprocessing detection
    if use_multiprocessing is None:
      use_multiprocessing = self._should_use_multiprocessing(file_tasks, topology)
    
    # Show performance info for larger topologies 
    if len(file_tasks) > 50:
      strings.print_colored_text('[PERF]    ','bright_yellow','Processing ')
      print(f"{len(file_tasks)} files for {len(topology.nodes)} nodes using {'multiprocessing' if use_multiprocessing else 'single-threaded'} mode")
    
    progress_queue = None
    progress_thread = None

    if show_progress:
      progress_queue = Queue()
      progress_thread = threading.Thread(
        target=_progress_monitor_lightweight, 
        args=(progress_queue, len(file_tasks), "File processing"),
        daemon=True
      )
      progress_thread.start()
    
    try:
      if use_multiprocessing and len(file_tasks) > 10 and multiprocessing.cpu_count() > 1:
        self._process_files_multiprocessing(file_tasks, shared_data, progress_queue, topology)
      else:
        self._process_files_single_threaded(file_tasks, shared_data, template_cache, progress_queue)
    finally:
      # Clean up
      if progress_queue:
        progress_queue.put(0)
      if progress_thread and progress_thread.is_alive():
        progress_thread.join(timeout=1.0)
    
    # Show performance summary
    if len(file_tasks) > 50:
      elapsed_time = time.monotonic() - start_time
      strings.print_colored_text('[PERF]    ','bright_green','Completed ')
      print(f"in {elapsed_time:.1f}s ({len(file_tasks)/elapsed_time:.0f} files/sec)")
  
  def _collect_file_tasks(self, topology: Box, inkey: str, outkey: str, template_cache: dict) -> list:
    """Collect all file tasks that need processing"""
    file_tasks = []
    
    for node in topology.nodes.values():
      binds = node.get(f'{self.provider}.{outkey}',None)
      if not binds:
        continue
        
      out_folder = f"{self.provider}_files/{node.name}"
      bind_dict = filemaps.mapping_to_dict(binds)
      
      for file, mapping in bind_dict.items():
        if not out_folder in file:
          continue
        file_name = file.replace(out_folder+"/","")
        template_name = self.find_extra_template(node, file_name, topology)
        if template_name:
          # Cache template path to avoid repeated template finding
          if template_name not in template_cache:
            template_cache[template_name] = {
              'in_folder': os.path.dirname(template_name),
              'j2': os.path.basename(template_name)
            }
          
          file_tasks.append({
            'node': node,
            'file_name': file_name,
            'template_name': template_name,
            'out_folder': out_folder,
            'mapping': mapping,
            'template_info': template_cache[template_name]
          })
    
    return file_tasks
  
  def _should_use_multiprocessing(self, file_tasks: list, topology: Box) -> bool:
    """Determine if multiprocessing should be used based on topology size"""
    total_files = len(file_tasks)
    total_nodes = len(topology.nodes)
    
    return (
      total_files > 20 or 
      (total_nodes > 10 and total_files > 5) or  
      (total_nodes > 5 and total_files > 10)   
    )
  
  def _process_files_single_threaded(self, file_tasks: list, shared_data: dict, template_cache: dict, progress_queue: Queue = None) -> None:
    """Process files using single-threaded approach with minimal progress overhead"""
    total_files = len(file_tasks)
    
    if progress_queue and total_files > 200:
      update_interval = max(10, total_files // 20)
      
      for i, task in enumerate(file_tasks):
        self._process_single_file(task, shared_data, template_cache)
        if (i + 1) % update_interval == 0:
          progress_queue.put(update_interval)
      
      # Send final progress update
      remaining = total_files % update_interval
      if remaining > 0:
        progress_queue.put(remaining)
    else:
      for task in file_tasks:
        self._process_single_file(task, shared_data, template_cache)
  
  def _process_files_multiprocessing(self, file_tasks: list, shared_data: dict, progress_queue: Queue = None, topology: Box = None) -> None:
    """Process files using multiprocessing for better performance with optional progress reporting"""
    # Convert shared_data to serializable format for multiprocessing
    serializable_shared_data = self._prepare_serializable_data(shared_data)
    
    # Prepare tasks for multiprocessing
    mp_tasks = self._prepare_multiprocessing_tasks(file_tasks)
    
    # Use multiprocessing with appropriate number of workers
    available_cores = multiprocessing.cpu_count()
    
    # Get max_workers from topology defaults with smart fallback
    max_workers = None
    if topology and hasattr(topology, 'defaults'):
      if hasattr(topology.defaults, 'multiprocessing') and hasattr(topology.defaults.multiprocessing, 'max_workers'):
        max_workers = topology.defaults.multiprocessing.max_workers
      elif hasattr(topology.defaults, 'max_workers'):
        max_workers = topology.defaults.max_workers
    
    if max_workers is None or max_workers == {}:
      if available_cores <= 4:
        max_workers = available_cores
      else:
        max_workers = int(available_cores * 0.75)
    
    # never exceed task count)
    num_workers = min(len(mp_tasks), max_workers)
    
    strings.print_colored_text('[WORKERS]    ','bright_yellow','Using ')
    if max_workers == available_cores:
      print(f"{num_workers} workers (using all {available_cores} available cores)")
    elif max_workers == int(available_cores * 0.75):
      print(f"{num_workers} workers (auto-scaled to 75% of {available_cores} available cores)")
    else:
      print(f"{num_workers} workers (configured: {max_workers}, available cores: {available_cores})")
    
    if topology and hasattr(topology, 'defaults') and hasattr(topology.defaults, 'multiprocessing') and hasattr(topology.defaults.multiprocessing, 'show_progress') and topology.defaults.multiprocessing.show_progress:
      strings.print_colored_text('[PROGRESS]  ','bright_cyan','Progress tracking ')
      print("enabled (slower but informative)")
    else:
      strings.print_colored_text('[PROGRESS]  ','bright_cyan','Progress tracking ')
      print("disabled (faster) - add 'show_progress: true' to defaults.multiprocessing if needed")

    # Process in chunks for progress reporting
    if progress_queue and len(mp_tasks) > 100:
      chunk_size = max(1, len(mp_tasks) // (num_workers * 2))  # Fewer chunks to reduce overhead
      self._process_chunks_with_progress(mp_tasks, serializable_shared_data, num_workers, chunk_size, progress_queue, file_tasks)
    else:
      # no progress overhead
      with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(self._process_file_worker, 
                          [(task, serializable_shared_data) for task in mp_tasks])
      self._handle_multiprocessing_results(results, file_tasks)
  
  def _process_chunks_with_progress(self, mp_tasks: list, serializable_shared_data: dict, 
                                  num_workers: int, chunk_size: int, progress_queue: Queue, file_tasks: list) -> None:
    """Process tasks in chunks to enable progress reporting"""
    chunks = [mp_tasks[i:i + chunk_size] for i in range(0, len(mp_tasks), chunk_size)]
    all_results = []
    
    with multiprocessing.Pool(processes=num_workers) as pool:
      for chunk in chunks:
        chunk_args = [(task, serializable_shared_data) for task in chunk]
        chunk_results = pool.map(self._process_file_worker, chunk_args)
        all_results.extend(chunk_results)
        
        if progress_queue:
          progress_queue.put(len(chunk))
    
    self._handle_multiprocessing_results(all_results, file_tasks)
  
  def _prepare_serializable_data(self, shared_data: dict) -> dict:
    """Convert shared_data to serializable format for multiprocessing"""
    return {
      'hostvars': dict(shared_data['hostvars']),
      'hosts': dict(shared_data['hosts']),
      'addressing': dict(shared_data['addressing'])
    }
  
  def _prepare_multiprocessing_tasks(self, file_tasks: list) -> list:
    """Prepare tasks for multiprocessing by converting to serializable format"""
    mp_tasks = []
    for task in file_tasks:
      mp_task = {
        'node_name': task['node'].name,
        'node_data': dict(task['node']),
        'file_name': task['file_name'],
        'template_name': task['template_name'],
        'template_info': task['template_info'],
        'out_folder': task['out_folder'],
        'mapping': task['mapping'],
        'provider': self.provider
      }
      mp_tasks.append(mp_task)
    return mp_tasks
  
  def _handle_multiprocessing_results(self, results: list, file_tasks: list) -> None:
    """Handle results from multiprocessing and display output"""
    for i, result in enumerate(results):
      if result.get('success'):
        task = file_tasks[i]
        strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
        sys_folder = str(_files.get_moddir())+"/"
        print(f"{task['out_folder']}/{task['file_name']} to {task['node'].name}:{task['mapping']} (from {task['template_name'].replace(sys_folder,'')})")
      else:
        log.error(f"Failed to process file: {result.get('error', 'Unknown error')}", 
                 log.IncorrectValue, self.provider)

  def _process_single_file(self, task: dict, shared_data: dict, template_cache: dict) -> None:
    """Process a single file task"""
    node = task['node']
    file_name = task['file_name']
    template_name = task['template_name']
    out_folder = task['out_folder']
    template_info = task['template_info']
    
    node_data = {**shared_data, **node}
    
    # Create subdirectory if needed
    if '/' in file_name:
      pathlib.Path(f"{out_folder}/{os.path.dirname(file_name)}").mkdir(parents=True,exist_ok=True)
    
    # Render template
    try:
      templates.write_template(
        in_folder=template_info['in_folder'],
        j2=template_info['j2'],
        data=node_data.to_dict(),
        out_folder=out_folder, 
        filename=file_name)
    except Exception as ex:
      log.fatal(
        text=f"Error rendering {template_name} into {file_name}\n{strings.extra_data_printout(str(ex))}",
        module=self.provider)

    strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
    sys_folder = str(_files.get_moddir())+"/"
    print(f"{out_folder}/{file_name} to {node.name}:{task['mapping']} (from {template_name.replace(sys_folder,'')})")
  
  @staticmethod
  def _process_file_worker(args: tuple) -> dict:
    """Worker function for multiprocessing file processing"""
    try:
      task, shared_data = args
      
      # Reconstruct node object
      node = type('Node', (), task['node_data'])()
      node.name = task['node_name']
      
      # Create node-specific data
      node_data = {**shared_data, **task['node_data']}
      
      file_name = task['file_name']
      template_info = task['template_info']
      out_folder = task['out_folder']
      
      if '/' in file_name:
        pathlib.Path(f"{out_folder}/{os.path.dirname(file_name)}").mkdir(parents=True,exist_ok=True)
      
      templates.write_template(
        in_folder=template_info['in_folder'],
        j2=template_info['j2'],
        data=node_data,
        out_folder=out_folder, 
        filename=file_name)
      
      return {'success': True}
      
    except Exception as ex:
      return {'success': False, 'error': str(ex)}

  def create(self, topology: Box, fname: typing.Optional[str]) -> None:
    self.transform(topology)
    fname = self.get_output_name(fname,topology)
    tname = self.get_root_template()
    try:
      r_text = templates.render_template(
        data=topology.to_dict(),
        j2_file=tname,
        path=self.get_template_path(),
        extra_path=_files.get_search_path(self.provider))
    except Exception as ex:
      log.fatal(
        text=f"Error rendering {fname} from {tname}\n{strings.extra_data_printout(str(ex))}",
        module=self.provider)

    _files.create_file_from_text(fname,r_text)
    if fname != '-':
      log.status_created()
      print(f"provider configuration file: {fname}")
      self.post_configuration_create(topology)
    else:
      print("\n")

  def post_start_lab(self, topology: Box) -> None:
    pass

  def pre_start_lab(self, topology: Box) -> None:
    pass

  def pre_stop_lab(self, topology: Box) -> None:
    pass

  def post_stop_lab(self, topology: Box) -> None:
    pass

  def post_configuration_create(self, topology: Box) -> None:
    pass

  def get_lab_status(self) -> Box:
    return get_empty_box()
  
  def get_node_name(self, node: str, topology: Box) -> str:
    return node

  """
  Generic provider pre-transform processing: Mark multi-provider links
  """
  def pre_transform(self,topology : Box) -> None:
    if not 'links' in topology:
      return

    for l in topology.links:
      for intf in l.interfaces:
        node = topology.nodes[intf.node]
        if not 'provider' in node:
          continue

        p_name = topology.provider                          # Get primary and secondary provider
        s_name = node.provider                              # ... to make the rest of the code more readable
        if p_name == s_name:                                # ... nothing to do if they're the same
          continue

        l[p_name].provider[s_name] = True                   # Collect secondary link provider(s)
        if 'uplink' in l[p_name]:                           # ... and copy primary uplink to secondary uplink
          l[s_name].uplink = l[p_name].uplink

  """
  Generic provider pre-output transform: remove loopback links
  """
  def pre_output_transform(self, topology: Box) -> None:
    if not 'links' in topology:
      return

    topology.links = [
      link for link in topology.links if link.type not in links.VIRTUAL_INTERFACE_TYPES ]

"""
select_primary_provider: Find the top provider for the topology. For example, you can have
clab nodes under libvirt provider, but not vice versa
"""
def select_primary_provider(topology: Box) -> None:
  p_default = topology.provider

  # Build a set of all providers used in the topology
  #
  p_set = { ndata.provider if 'provider' in ndata else p_default for ndata in topology.nodes.values() }
  if len(p_set) == 1:                             # Single-provider topology
    p_used = list(p_set)[0]
    if p_default != p_used:                       # ... but not using the (default) primary provider
      log.warning(
        text=f'Topology provider changed from {p_default} to {p_used}. Nodes are not affected',
        flag='providers.change',
        module='providers')
      topology.provider = p_used
      topology.defaults.provider = p_used
      return

  # Now build the list of providers that can be mixed (in relative order)
  p_mix_list = [ x for x in topology.defaults.const.multi_provider if x in p_set ]
  if not p_mix_list:                              # No relevant providers
    return
  
  # Select the top provider from that list
  p_top = p_mix_list[0]
  if p_top == p_default:
    return                                        # No need to change the top provider

  topology.provider = p_top                       # Change the top provider
  topology.defaults.provider = p_top
  for ndata in topology.nodes.values():           # Now set the explicit providers for all nodes that need it
    if not 'provider' in ndata:
      ndata.provider = p_default

  log.warning(
    text=f'Topology provider changed from {p_default} to {p_top}. Nodes are not affected',
    flag='providers.change',
    module='providers')

"""
Get a pointer to provider module. Cached in topology._Providers
"""
def get_provider_module(topology: Box, pname: str) -> _Provider:
  if not pname in topology._Providers:
    topology._Providers[pname] = _Provider.load(pname,topology.defaults.providers[pname])

  return topology._Providers[pname]

"""
Execute a topology-wide provider hook
"""
def execute(hook: str, topology: Box) -> None:
  p_module = get_provider_module(topology,topology.provider)
  p_module.call(hook,topology)

  for node in topology.nodes.values():
    execute_node(f'node_{hook}',node,topology)

"""
Execute a node-level provider hook
"""
def execute_node(hook: str, node: Box, topology: Box) -> typing.Any:
  node_provider = devices.get_provider(node,topology.defaults)
  p_module = get_provider_module(topology,node_provider)
  return p_module.call(hook,node,topology)

"""
Mark all nodes and links with relevant provider(s)
"""
def mark_providers(topology: Box) -> None:
  for n in topology.nodes.values():                 # Set 'provider' attribute on all nodes
    if 'provider' in n:
      continue

    n.provider = topology.provider

  for l in topology.links:                          # Set 'providers' attribute on all links
    for intf in l.interfaces:
      if intf.node not in topology.nodes:
        continue
      node = topology.nodes[intf.node]
      l.provider[node.provider] = True

"""
Select a subset of the topology -- links and nodes relevant to the current provider
"""
def select_topology(topology: Box, provider: str) -> Box:
  topology = get_box(topology)                      # Create a copy of the topology
  for n in list(topology.nodes.keys()):             # Remove all nodes not belonging to the current provider
    if topology.nodes[n].provider != provider:
      topology.nodes[n].unmanaged = True
#      topology.nodes.pop(n,None)

  topology.links = [ l for l in topology.links if provider in l.provider ]      # Retain only the links used by current provider
  return topology

"""
get_forwarded_ports -- build a list of default provider forwarded ports for the specified node
"""
def get_provider_forwarded_ports(node: Box, topology: Box) -> list:
  p = devices.get_provider(node,topology.defaults)
  fmap = topology.defaults.providers[p].get('forwarded',{})     # Provider-specific forwarded ports
  if not fmap:                                                  # No forwarded ports?
    return []                                                   # ... return an empty list

  pmap = topology.defaults.ports                                # Mappings of port names into TCP numbers
  node_fp = []                                                  # Forwarded ports for the current node

  for fp,fstart in fmap.items():                                # Iterate over forwarded ports
    if not fp in pmap:                                          # Is the port we're trying to forward known to netlab?
      continue                                                  # ... nope, bad luck, move on
    node_fp.append([ fstart + node.id, pmap[fp]])               # Append [host,device] port mapping

  return node_fp

def node_add_forwarded_ports(node: Box, fplist: list, topology: Box) -> None:
  if not fplist:
    return

  p = devices.get_provider(node,topology.defaults)
  for port_map in fplist:                                       # Iterate over forwarded port mappings
    port_map_string = f'{port_map[0]}:{port_map[1]}'            # Build the provider-compatible map entry
    append_to_list(node[p],'ports',port_map_string)             # ... and add it to the list of forwarded ports

"""
validate_images -- check the images used by individual nodes against provider image repo
"""
def validate_images(topology: Box) -> None:

  for n_data in topology.nodes.values():
    execute_node('validate_node_image',n_data,topology)

  log.exit_on_error()

"""
validate_mgmt_ip -- Validate management IP addresses
"""
def validate_mgmt_ip(
      node: Box,
      provider: str,
      mgmt: Box,
      required: bool = False,
      v4only: bool = False) -> None:

  valid_af = ['ipv4'] if v4only else ['ipv4','ipv6']
  n_mgmt = node.mgmt
  node_af = [ n_af for n_af in n_mgmt.keys() if n_af in valid_af ]
  if not node_af and required:
    log.error(
      f'Node {node.name} must have {" or ".join(valid_af)} management address',
      category=log.MissingValue,
      module=provider)

  if not mgmt:
    return

  for af in ['ipv4','ipv6']:
    if af not in n_mgmt:
      continue
    m_addr = ipaddress.ip_interface(n_mgmt[af])
    pfx = mgmt.get(f'{af}_pfx',None)
    if pfx is None:
      log.error(
        f'Node {node.name} has an {af} management address, but the mgmt pool does not have an {af} prefix',
        category=log.IncorrectValue,
        module=provider)
    elif not m_addr.network.subnet_of(pfx):
      log.error(
        f'Management {af} address of node {node.name} ({n_mgmt[af]}) is not part of the management subnet',
        category=log.IncorrectValue,
        module=provider)
