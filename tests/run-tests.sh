#!/bin/bash
if [ "$1" == "ci" ]; then
  set -e
fi
DIRNAME=`dirname "$0"`
echo "Executing CI/CD tests in $DIRNAME"
cd "$DIRNAME"
PYTHONPATH="../" python3 -m pytest -vvv -k 'xform_ or error_cases'
#
# Remove files unnecessarily created by various provider modules
# (until we fix that)
#
rm -fr *files
set -e
cd ..; python3 -m mypy -p netsim
for file in netsim/extra/*/plugin.py; do
  python3 -m mypy $file
done
if [ `which yamllint` ]; then
  echo
  echo Executing yamllint in netsim and tests directories
  yamllint --no-warnings netsim/*yml netsim/**/*yml tests/**/*yml
else
  echo
  echo Install yamllint with pip3 install -r requirements-dev.txt
  exit 1
fi