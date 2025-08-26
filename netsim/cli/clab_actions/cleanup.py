#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import sys

from box import Box

from ...utils import log, strings
from .. import external_commands


def cleanup_parser(parser: argparse.Namespace) -> None:
  parser.add_argument(
    '-f','--force',
    dest='force',
    action='store_true',
    help='Perform the cleanup without asking for confirmation')

def cleanup_confirm() -> None:
  log.section_header('WARNING','Read this first','yellow')
  print("""
The 'netlab clab cleanup' command can be used to cleanup Docker environment
after a particularly bad containerlab-related failure. It will kill all running
containers, and purge the containers and Docker networks.
        
Use this command only as a last resort when 'netlab down --cleanup' fails to do
its job. You might also use 'netlab clab cleanup' followed by 'netlab down
--cleanup' to recover from situations in which containerlab refuses to bring
down the lab.
""")
  if not strings.confirm('Do you want to continue?'):
    print('User decided to abort the container cleanup process')
    sys.exit(1)

def clab_cleanup(args: argparse.Namespace, settings: Box) -> None:
  if not args.force:
    cleanup_confirm()
  
  print()
  docker_ps = external_commands.run_command(
    [ "docker", "ps", "--format", "{{ .Names }}" ],
    check_result=True,
    return_stdout=True)
  if isinstance(docker_ps,str):
    clist = [ cname for cname in docker_ps.split("\n") if cname ]
    external_commands.print_step(1,"Killing all running containers")
    external_commands.run_command([ 'docker', 'kill' ] + clist)
  else:
    log.info('No containers are running, skipping the first step','clab')

  external_commands.print_step(2,"Purging containers and Docker networks",spacing = True)
  external_commands.run_command('docker system prune -f')
