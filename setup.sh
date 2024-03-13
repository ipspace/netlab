#!/bin/bash
me=${BASH_SOURCE:-$_}
echo "Adding netlab Git repository to the search path"
dir=$(pwd)
if [ -z "$me" ]; then
  echo "Cannot figure out who I am. Aborting..."
else
  cd $(dirname "$me")
  pwd=$(pwd)
  export PATH=$pwd:$PATH
  echo "... added $pwd to PATH"
  cd "$dir"
fi
