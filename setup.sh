#!/bin/bash
echo "Set up paths for netsim-tools downloaded from Github"
echo
dir=$(pwd)
if [ "$BASH_SOURCE" == "$0" ]; then
  echo "Run the setup script as 'source $BASH_SOURCE'"
else
  cd $(dirname "$BASH_SOURCE")
  pwd=$(pwd)
  export PATH=$pwd:$pwd/netsim/ansible:$pwd/shell:$PATH
  echo "added $pwd and [ansible,shell] directories to PATH"
  cd "$dir"
fi
