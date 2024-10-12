import os
import typing

from netsim import __version__
from netsim.utils import log, files as _files,strings
from netsim import data

from box import Box

def cleanup(topology: Box) -> None:
  missing = data.get_empty_box()
  for ndata in topology.nodes.values():
    if not 'config' in ndata:
      continue

    candidate_files = [
      f'{ndata.name}.{ndata.device}.j2',
      f'{ndata.name}.j2',
      f'{ndata.device}.j2' ]

    for cfg in list(ndata.config):
      for cfg_candidate in candidate_files:
        cfg_file = _files.find_file(f'{cfg}/{cfg_candidate}',topology.defaults.paths.custom.dirs)

        if cfg_file:
          break

      if cfg_file:
        break

      cfg_id = strings.make_id(cfg)
      missing[cfg_id].item = cfg
      data.append_to_list(missing[cfg_id].devices,ndata.device,ndata.name)
      ndata.config = [ f for f in ndata.config if f != cfg ]

  hint: typing.Optional[str] = "You will have to configure the missing functionality yourself"
  for m_config in missing.values():
    for m_device,m_nodes in m_config.devices.items():
      log.error(
        f'Custom configuration {m_config.item} is missing for device {m_device} (nodes {",".join(m_nodes)})',
        category=Warning,
        more_hints=hint,
        module='check.config')
      hint = None
