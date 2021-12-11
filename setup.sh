#!/bin/bash
me=${BASH_SOURCE:-$_}
echo "Set up paths for netsim-tools downloaded from Github"
echo
dir=$(pwd)
if [ -z "$me" ]; then
  echo "Cannot figure out who I am. Aborting..."
else
  cd $(dirname "$me")
  pwd=$(pwd)
  export PATH=$pwd:$pwd/netsim/ansible:$PATH
  echo "added $pwd and netsim/ansible directories to PATH"
  cd "$dir"
fi
