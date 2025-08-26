# Implement simple sorting routines

import typing

from . import log

'''
Sort objects based on their dependencies

Given a name of an object, the 'get_dependency' callable should return
the list of object names this object depends on.

The function tries to sort object based on their dependencies using a very
simple algorithm that iterates over the list of remaining objects as many
times as needed (with the initial length of the list being a safeguard)

* Take the next object from the list
* Is there another object in the remaining objects list that this one
  depends on? If so skip it, otherwise it's safe to add the object
  to the sorted list.
'''

def dependency(mods: list, get_dependency: typing.Callable[[str],list]) -> list:
  if (len(mods) < 2):
    return mods

  watchdog_counter = len(mods)

  output: typing.List[str] = []
  while len(mods):
    skipped: typing.List[str] = []
    for m in mods:
      requires = get_dependency(m)
      if [ r for r in requires if r in mods ]:
        skipped = skipped + [ m ]
      else:
        output = output + [ m ]

    mods = skipped
    watchdog_counter -= 1
    if (watchdog_counter < 0):
      raise log.FatalError('dependency sort encountered a loop')

  return output
