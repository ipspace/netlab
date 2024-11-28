#!/bin/bash
DIRNAME=`dirname "$0"`
cd "$DIRNAME"
cd ..
if [ `which yamllint` ]; then
  echo Run yamllint
  yamllint --no-warnings netsim/*yml netsim/**/*yml tests/**/*yml
else
  echo Install yamllint with pip3 install -r requirements-dev.txt
  exit 1
fi