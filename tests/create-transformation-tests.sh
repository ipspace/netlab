#!/bin/bash
#
# Assuming the topology transformation code is working correctly, create
# numerous test cases for future use. Iterate through all topology*yml
# files, run transformation on them, and write the results into
# exp-topology*yml files (expected results)
#
set -e
XFORM_PATH="topology/input"

# Check for "coverage" first
if [[ "$1" == "coverage" ]]; then
    echo "Creating code coverage transformation tests"
    XFORM_PATH="coverage/input"
    shift
fi

# If no args left, default to "*"
if [[ $# -eq 0 ]]; then
    set -- "*"
fi

for arg in "$@"; do
  for file in ${XFORM_PATH}/${arg}.yml; do
    PYTHONPATH="../" python3 create-transformation-test-case.py -t $file
  done
done
#
# Remove files unnecessarily created by various provider modules
# (until we fix that)
#
rm -fr *files
