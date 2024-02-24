#!/bin/bash
DIRNAME=`dirname "$0"`
echo "Executing CI/CD tests in $DIRNAME"
cd "$DIRNAME"
PYTHONPATH="../" python3 -m pytest -vvv
#
# Remove files unnecessarily created by various provider modules
# (until we fix that)
#
rm -fr *files
set -e
cd ..; python3 -m mypy --no-incremental -p netsim
for file in netsim/extra/*/plugin.py; do
  python3 -m mypy $file
done
