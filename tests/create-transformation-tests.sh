#!/bin/bash
#
# Assuming the topology transformation code is working correctly, create
# numerous test cases for future use. Iterate through all topology*yml
# files, run transformation on them, and write the results into
# exp-topology*yml files (expected results)
#
set -e
for file in topology/input/*yml; do
  PYTHONPATH="../" python3 create-transformation-test-case.py -t $file
done
