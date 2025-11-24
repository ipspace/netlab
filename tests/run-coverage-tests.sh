#!/bin/bash
if [ "$1" == "ci" ]; then
  set -e
fi
DIRNAME=`dirname "$0"`
echo "Executing code coverage tests in $DIRNAME"
cd "$DIRNAME"
PYTHONPATH="../" python3 -m pytest -vvv -k 'coverage'
#
# Remove files unnecessarily created by various provider modules
# (until we fix that)
#
rm -fr *files
