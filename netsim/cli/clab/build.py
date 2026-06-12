#
# netlab clab build command
#
# Build custom container images
#
import argparse
import os
import pathlib
import re
import tempfile
import typing

import requests
from box import Box

from ...augment import devices
from ...utils import files as _files
from ...utils import log, strings, templates
from ...utils import read as _read
from .. import external_commands

SW_VERSION_ARG = re.compile(r'^\s*ARG\s+SW_VERSION\b', re.MULTILINE)
SW_DOWNLOAD_URL_ARG = re.compile(r'^\s*ARG\s+SW_DOWNLOAD_URL\b', re.MULTILINE)


def build_parser(parser: argparse.ArgumentParser) -> None:
  """Add CLI arguments for the **netlab clab build** command."""
  parser.add_argument(
    '-l','--list',
    dest='list',
    action='store_true',
    help='List available routing daemons')

  parser.add_argument(
    '-t','--tag',
    dest='tag',
    action='store',
    help='Specify a non-default tag for the container image')

  parser.add_argument(
    dest='image',
    action='store',
    nargs='?',
    help='Routing daemon name')

def get_dockerfiles() -> dict:
  """Return a mapping of build target names to Dockerfile paths.

  Build target names combine the daemon directory name with any Dockerfile suffix
  (for example, ``bird.v2_from_src`` maps to ``daemons/bird/Dockerfile.v2_from_src``).
  """
  d_path = _files.get_traversable_path('package:daemons')
  d_list = _files.get_globbed_files(d_path,'*/Dockerfile*')

  df_dict: dict = {}

  for d_file in d_list:
    daemon = os.path.basename(os.path.dirname(d_file))
    root, ext = os.path.splitext(d_file)
    # If the Dockerfile has a .j2 extension, keep it in the key name
    ext = ext.replace('.j2', '')
    df_dict[daemon + ext] = d_file

  return df_dict

def get_description(dfname: str) -> str:
  """Extract the ``description=`` value from a Dockerfile ``LABEL`` line."""
  try:
    df_lines = pathlib.Path(dfname).read_text().split('\n')
    for line in df_lines:
      if not line.startswith('LABEL'):
        continue
      if not 'description=' in line:
        continue
      return line.split('description=')[1].replace('"','')

  except:
    return '-- failed --'

  return '???'

def get_device_name(df_path: str) -> str:
  """Return the daemon/device name from a Dockerfile path (the parent directory name)."""
  return os.path.basename(os.path.dirname(df_path))

def dockerfile_uses_sw_version(df_path: str) -> bool:
  """Return ``True`` if the Dockerfile declares ``ARG SW_VERSION``."""
  return bool(SW_VERSION_ARG.search(pathlib.Path(df_path).read_text()))

def dockerfile_uses_sw_download_url(df_path: str) -> bool:
  """Return ``True`` if the Dockerfile declares ``ARG SW_DOWNLOAD_URL``."""
  return bool(SW_DOWNLOAD_URL_ARG.search(pathlib.Path(df_path).read_text()))

def get_sw_version(device: str, defaults: Box) -> typing.Optional[str]:
  """Return the software version to build.

  Resolution order: ``SW_VERSION`` environment variable, then ``clab.sw_version`` in device defaults.
  """
  env_version = os.environ.get('SW_VERSION')
  if env_version:
    return env_version

  node = Box({'device': device, 'provider': 'clab'}, default_box=True, box_dots=True)
  return devices.get_provider_data(node,defaults).get('sw_version',None)

def get_sw_download_url(device: str, sw_version: str, defaults: Box) -> typing.Optional[str]:
  """Return the source download URL with ``{sw_version}`` substituted in ``clab.sw_download_url``."""
  node = Box({'device': device, 'provider': 'clab'}, default_box=True, box_dots=True)
  url_template = devices.get_provider_data(node,defaults).get('sw_download_url',None)
  if not url_template:
    return None

  return url_template.replace('{sw_version}',sw_version)

def verify_sw_download(url: str, sw_version: str, device: str) -> None:
  """Verify that the source tarball exists at *url* before starting a Docker build.

  Issues a fatal error when the HTTP ``HEAD`` request fails or returns a non-success status code.
  """
  try:
    response = requests.head(url, allow_redirects=True, timeout=30)
  except requests.RequestException as ex:
    log.fatal(
      '\n'.join([
        f'Cannot verify {device} version {sw_version} at {url}: {ex}',
        'Check your network connection and the download URL in device defaults.',
        f'Set SW_VERSION or defaults.daemons.{device}.clab.sw_version to a valid release.',
      ]),
      module='build')

  if response.ok:
    return

  log.fatal(
    '\n'.join([
      f'Cannot download {device} version {sw_version}: {url} (HTTP {response.status_code})',
      'See the vendor download page for valid releases.',
      f'Set SW_VERSION or defaults.daemons.{device}.clab.sw_version to an existing version.',
    ]),
    module='build')

def render_j2_dockerfile(df_path: str, tmp_dir: str, defaults: Box) -> str:
  """Render a ``Dockerfile.j2`` template and return the path to use for ``docker build``.

  Regular Dockerfiles are returned unchanged. Jinja2 templates are rendered with *defaults*
  into *tmp_dir* as ``Dockerfile``.
  """
  if not df_path.endswith('.j2'):
    return df_path  # Regular Dockerfile, use as-is

  strings.print_colored_text('[TEMPLATE] ','cyan',None)
  print(f"Rendering Jinja2 template from {os.path.basename(df_path)}")

  # Render template (fail() is available as a standard Jinja2 global function)
  try:
    templates.write_template(
      os.path.dirname(df_path),
      os.path.basename(df_path),
      {'defaults': defaults},
      tmp_dir,
      'Dockerfile')
  except Exception as ex:
    log.fatal(
      f'Failed to render Dockerfile template {os.path.basename(df_path)}: {str(ex)}',
      module='build')

  strings.print_colored_text('[RENDERED] ','green',None)
  print("Template rendered to temporary Dockerfile")

  return os.path.join(tmp_dir, 'Dockerfile')

def print_sw_version_build_hint(device: str, sw_version: str) -> None:
  """Print a user hint after a failed build when source download errors were detected."""
  build_output = external_commands.CAPTURED_STDOUT + external_commands.CAPTURED_STDERR
  if 'ERROR: Cannot download' not in build_output and '404 Not Found' not in build_output:
    return

  print()
  strings.print_colored_text('[HINT]     ','yellow',None)
  print(f'{device} version {sw_version} could not be downloaded.')
  print('Pick a valid release or change SW_VERSION / clab.sw_version.')

def build_image(image: str, tag: typing.Optional[str], defaults: Box) -> None:
  """Build a daemon container image with ``docker build``.

  Resolves software version and download URL settings, verifies remote tarballs when configured,
  and passes ``SW_VERSION`` / ``SW_DOWNLOAD_URL`` build arguments to Docker when the selected
  Dockerfile declares the corresponding ``ARG`` instructions.
  """
  df_dict = get_dockerfiles()
  if not image in df_dict:
    log.fatal(f'Unknown daemon/image {image}, use "netlab clab build -l" to list available images')

  df_path = df_dict[image]
  device = get_device_name(df_path)
  workdir = os.getcwd()
  sw_version: typing.Optional[str] = None

  with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)

    dockerfile_to_use = render_j2_dockerfile(df_path, tmp, defaults)
    uses_sw_version = dockerfile_uses_sw_version(dockerfile_to_use)
    uses_sw_download_url = dockerfile_uses_sw_download_url(dockerfile_to_use)
    download_url: typing.Optional[str] = None

    if uses_sw_version:
      sw_version = get_sw_version(device,defaults)
      if not sw_version:
        log.fatal(
          '\n'.join([
            f'Cannot build {image}: no software version specified.',
            'Set the SW_VERSION environment variable or '
            f'defaults.daemons.{device}.clab.sw_version',
          ]),
          module='build')

      download_url = get_sw_download_url(device,sw_version,defaults)
      if uses_sw_download_url and not download_url:
        log.fatal(
          '\n'.join([
            f'Cannot build {image}: no software download URL specified.',
            f'Set defaults.daemons.{device}.clab.sw_download_url',
          ]),
          module='build')

      if download_url:
        strings.print_colored_text('[CHECKING] ','cyan',None)
        print(f"Verifying {device} version {sw_version} at {download_url}")
        verify_sw_download(download_url,sw_version,device)

    if tag is None or not tag:
      tag = f'netlab/{image}:{sw_version}' if sw_version else f'netlab/{image}:latest'

    strings.print_colored_text('[STARTING] ','green',None)
    print(f"Building container image {image} with tag {tag}")
    if sw_version:
      print(f"Software version: {sw_version}")

    strings.print_colored_text('[WORKING]  ','green',None)
    print(f"Trying to remove existing container image {tag}")

    if external_commands.run_command(f'docker image rm {tag}',ignore_errors=True,check_result=False):
      strings.print_colored_text('[REMOVED]  ','green',None)
      print(f"Removed existing image {tag}")
    else:
      strings.print_colored_text('[HICCUP]   ','yellow',None)
      print(f"Cannot remove image {tag}, continuing")

    strings.print_colored_text('[WORKING]  ','green',None)
    print("Prune docker layers and builder cache")
    external_commands.run_command('docker image prune -f',ignore_errors=True)
    external_commands.run_command('docker builder prune -f',ignore_errors=True)

    print()
    strings.print_colored_text('[WORKING]  ','green',None)
    print(f"Building container image {tag}")

    build_cmd: typing.List[str] = ['docker','build','-t',tag,'-f',dockerfile_to_use]
    if sw_version:
      build_cmd.extend(['--build-arg',f'SW_VERSION={sw_version}'])
    if download_url:
      build_cmd.extend(['--build-arg',f'SW_DOWNLOAD_URL={download_url}'])
    build_cmd.append('.')

    status = external_commands.run_command(
      build_cmd,
      ignore_errors=True,
      check_result=False)
    if status:
      strings.print_colored_text('[FINISHED] ','green',None)
      print(f"Container image {tag} for {image} daemon built and installed")
    else:
      strings.print_colored_text('[FAILED]   ','red',None)
      print(f"Failed to build the container image {tag} for {image} daemon")
      if sw_version:
        print_sw_version_build_hint(device,sw_version)

  os.chdir(workdir)
  print()
  external_commands.run_command(f'docker image ls {tag}',ignore_errors=True)

def list_dockerfiles() -> None:
  """List available daemon Dockerfiles and their default container tags."""
  rows = []
  df_dict = get_dockerfiles()
  for daemon in sorted(df_dict.keys()):
    # Strip .j2 extension from daemon name if present for display
    display_name = daemon.replace('.j2', '')
    rows.append([display_name, f'netlab/{display_name}:latest', get_description(df_dict[daemon])])

  print("""
The 'netlab clab build' command can be used to build the following container images
""")
  strings.print_table(['daemon','default tag','description'],rows,inter_row_line=False)

def clab_build(args: argparse.Namespace, settings: Box) -> None:
  """Execute the **netlab clab build** subcommand."""
  if args.list:
    list_dockerfiles()
    return

  if args.image:
    try:
      topology = _read.system_defaults()
      devices.merge_daemons(topology)
    except Exception as ex:
      log.fatal(f'Could not load system defaults: {str(ex)}', module='build')
    build_image(args.image,args.tag,topology.defaults)
    return

  log.fatal('Specify image to build or "--list". Use "--help" to get help')
