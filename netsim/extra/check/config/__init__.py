
from box import Box

from netsim import data
from netsim.utils import files as _files
from netsim.utils import log, strings


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

  for m_config in missing.values():
    for m_device,m_nodes in m_config.devices.items():
      log.warning(
        text=f'Custom configuration {m_config.item} is missing for device {m_device} (nodes {",".join(m_nodes)})',
        more_hints='You will have to configure the missing functionality yourself',
        module='check.config')
