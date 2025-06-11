import typing
from box import Box
from netsim import api
from netsim.augment import devices
from netsim.utils import log

_config_name = "ospf.stub"
_require = [ "ospf" ]

def validate_area( id: int, area: Box ) -> None:
  if area.get('kind','normal') != 'normal' and 'range' in area:
    log.error(f"OSPF area {id} is of type {area.kind} and cannot support inter-area 'range' summarization")

def post_transform(topology: Box) -> None:
  for ndata in topology.nodes.values():
    if not 'ospf' in ndata.get('module',[]):
      continue
    ospf_areas = ndata.get('ospf.areas',{})
    if not ospf_areas:
      continue
    features = devices.get_device_features(ndata,topology.defaults)
    if 'stub' not in features.ospf:
      log.error(f"Node {ndata.name} (device {ndata.device}) not supported by the ospf.stub plugin")
      continue
    for k,v in ospf_areas.items():
      validate_area(k,v)
    if ndata.get('ospf.area','0.0.0.0') != '0.0.0.0':  # Check if node is not an ABR
      for _,area in ospf_areas.items():
        for att in [ 'no_summary', 'range' ]:          # Only applied at ABR
          area.pop(att,None)
    global _config_name
    api.node_config(ndata,_config_name)
