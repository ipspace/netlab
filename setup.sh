#!/bin/bash
me=${BASH_SOURCE:-$_}
echo "Adding netlab Git repository to the search path"
dir=$(pwd)
if [ -z "$me" ]; then
  echo "Cannot figure out who I am. Aborting..."
  exit 1
fi

cd $(dirname "$me")
pwd=$(pwd)
export PATH=$pwd:$PATH
echo "... added $pwd to PATH"

if [ -z "$PYTHONPATH" ]; then
  export PYTHONPATH=$pwd
  echo "... created PYTHONPATH"
else
  export PYTHONPATH=$pwd:$PYTHONPATH
  echo "... added $pwd to PYTHONPATH"
fi

cd "$dir"
