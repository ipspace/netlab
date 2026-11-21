#
# Render IS-IS configuration templates and check device-specific details
#
from netsim.utils.templates import render_template


def test_asa_isis_ipv6_multi_topology() -> None:
  data = {
    'id': 1,
    'isis': {'type': 'level-2', 'area': '49.0001', 'af': {'ipv4': True, 'ipv6': True}},
    'interfaces': [{'ifname': 'GigabitEthernet0/0', 'ipv4': '10.1.0.1/30', 'ipv6': '2001:db8:1::1/64', 'isis': {}}],
  }
  config = render_template(data=data, j2_file='asa.j2', path='ansible/templates/isis')
  assert '  address-family ipv6\n    multi-topology\n' in config
