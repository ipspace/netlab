#!/usr/bin/env python3
#
# Check the documentation URLs used in netlab error messages (doc_url parameters)
# against the HTML documentation built with Sphinx
#
# Usage: check-doc-urls.py <html-build-directory>
#
# The script finds all relative documentation URLs (string literals like
# 'module/bgp/#bgp-platform') in the netsim source code and checks that the target
# page exists and contains an element with the anchor ID. Sphinx replaces underscores
# in MyST anchors with hyphens, so a URL pointing to (routing_router_id)= anchor
# must use #routing-router-id
#
import re
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Documentation URLs are string literals with a relative page path and an anchor
URL_RE = re.compile(r"""(?:\bf)?(['"])([a-z][\w.{}/-]*/#[\w.{}-]+)\1""")

# Values used to expand variables in f-string URLs
EXPANSIONS: typing.Dict[str, typing.List[str]] = {
  'proto': [ 'ospf', 'isis', 'bgp', 'ripv2', 'eigrp' ],
  'f_name': [ 'gre', 'wireguard' ],
}

# URL-specific expansion values (for URLs used in code that is called for a subset of
# the generic values)
URL_EXPANSIONS: typing.Dict[str, typing.Dict[str, typing.List[str]]] = {
  'module/{proto}/#{proto}-interface-support': { 'proto': [ 'ospf' ] },  # Only OSPF has optional intf attributes
}

def find_urls() -> typing.List[typing.Tuple[str, int, str]]:
  """Find documentation URLs in the netsim source code, return (file, line, URL) tuples"""
  result = []
  for f in sorted((ROOT / 'netsim').rglob('*.py')):
    src = f.read_text()
    for m in URL_RE.finditer(src):
      result.append((str(f.relative_to(ROOT)), src.count('\n', 0, m.start()) + 1, m.group(2)))
  return result

def expand_url(url: str) -> typing.Tuple[typing.List[str], typing.Optional[str]]:
  """Expand f-string variables in a URL, return the list of URLs or an error message"""
  urls = [ url ]
  for var in set(re.findall(r'\{(\w+)\}', url)):
    values = URL_EXPANSIONS.get(url, {}).get(var) or EXPANSIONS.get(var)
    if not values:
      return [], f'no expansion values for variable {{{var}}}, add them to EXPANSIONS in {Path(__file__).name}'
    urls = [ u.replace(f'{{{var}}}', v) for u in urls for v in values ]
  return urls, None

_id_cache: typing.Dict[Path, typing.Set[str]] = {}

def check_url(url: str, html_dir: Path) -> typing.Optional[str]:
  """Check a single URL, return an error message or None"""
  page, _, anchor = url.partition('#')
  page = page.strip('/')
  html = html_dir / f'{page}.html'
  if not html.exists():                                       # Try the 'dirhtml' builder output
    html = html_dir / page / 'index.html'
  if not html.exists():
    return f'page {page} does not exist'
  if '_' in anchor:
    return f'anchor #{anchor} contains underscores (Sphinx replaces them with hyphens)'
  if html not in _id_cache:
    _id_cache[html] = set(re.findall(r'\bid="([^"]+)"', html.read_text()))
  if anchor not in _id_cache[html]:
    return f'anchor #{anchor} does not exist in {page}'
  return None

def main() -> None:
  if len(sys.argv) != 2:
    sys.exit(f'Usage: {sys.argv[0]} <html-build-directory>')
  html_dir = Path(sys.argv[1])
  if not html_dir.is_dir():
    sys.exit(f'{html_dir} is not a directory')

  entries = find_urls()
  err_cnt = 0
  for (fname, line, url) in entries:
    urls, err = expand_url(url)
    errors = [ err ] if err else [ e for e in (check_url(u, html_dir) for u in urls) if e ]
    for e in errors:
      print(f'{fname}:{line}: {url}: {e}')
      err_cnt += 1

  print(f'Checked {len(entries)} documentation URLs, found {err_cnt} errors')
  sys.exit(1 if err_cnt else 0)

if __name__ == '__main__':
  main()
