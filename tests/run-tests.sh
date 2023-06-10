#!/bin/bash
DIRNAME=`dirname $0`
echo "Executing tests in $DIRNAME"
cd $DIRNAME
PYTHONPATH="../" python3 -m pytest -vvv
#
# Remove files unnecessarily created by various provider modules
# (until we fix that)
#
rm -fr *files
cd ..; python3 -m mypy --no-incremental -p netsim
