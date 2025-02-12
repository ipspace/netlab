#!/usr/bin/env python3
#
import sys
import typing
import pathlib

from netsim import __version__
from netsim.cli import external_commands
from box import Box
from netsim.data import get_empty_box
from netsim.utils import log


def get_git_releases() -> dict:
  r_list = {}

  git_tags = external_commands.run_command('git tag',return_stdout=True,check_result=True)
  if not git_tags or not isinstance(git_tags,str):
    log.fatal('Cannot get a list of Git tags')

  for tag in git_tags.split('\n')[-10:]:
    if not tag:
      continue
    r_date = external_commands.run_command(
              ['git','log',tag,'-n','1','--format=format:%cd','--date=format:%Y-%m-%d %H:%M:%S'],
              return_stdout=True,
              check_result=True)
    if not r_date:
      log.fatal(f'Cannot get a commit date for {tag}')
    tag = tag.replace('release_','')
    r_list[tag] = r_date

  return r_list

def get_release_from_timestamp(t: str, r_list: dict) -> typing.Optional[str]:
  post_release = [ r_key for r_key in r_list.keys() if r_list[r_key] >= t ]
  return post_release[0] if post_release else None

def relabel_data(data: Box, r_list: dict) -> None:
  for k,v in data.items():
    if isinstance(v,Box):
      relabel_data(data[k],r_list)
    elif k == '_timestamp':
      release = get_release_from_timestamp(v,r_list)
      if release:
        data._version = release

def relabel_releases(glob: str, r_list: dict) -> None:
  for path in pathlib.Path('.').glob(glob):
    try:
      data = Box.from_yaml(filename=str(path))
    except Exception as Ex:
      print(f'Cannot read {path}: {Ex}')
      continue

    i_yaml = data.to_yaml()
    relabel_data(data,r_list)
    if data.to_yaml != i_yaml:
      print(f'Changed: {path}')
      data.to_yaml(filename=path)

def main() -> None:
  r_list = get_git_releases()
  relabel_releases('**/*yaml',r_list)

if __name__ == '__main__':
  main()
