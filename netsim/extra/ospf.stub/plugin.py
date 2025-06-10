import typing
from box import Box
from netsim import api

_config_name = "ospf.stub"
_require = [ "ospf" ]

def post_transform(topology: Box) -> None:
  for ndata in topology.nodes.values():
    if not 'ospf' in ndata.get('module',[]):
      continue
    ospf_areas = ndata.get('ospf.areas',{})
    if not ospf_areas:
      continue
    if ndata.get('ospf.area','0.0.0.0') != '0.0.0.0':  # Check if node is an ABR
      for _,area in ospf_areas.items():
        area.pop('no_summary',None)
    global _config_name
    api.node_config(ndata,_config_name)
