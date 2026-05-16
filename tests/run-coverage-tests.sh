#!/bin/bash
if [ "$1" == "ci" ]; then
  set -e
fi
DIRNAME=`dirname "$0"`
echo "Executing code coverage tests in $DIRNAME"
cd "$DIRNAME"
PYTHONPATH="../" python3 -m pytest -v -k 'coverage'
