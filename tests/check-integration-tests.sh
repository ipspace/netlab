#!/bin/bash
#
# Assuming the topology transformation code is working correctly, create
# numerous test cases for future use. Iterate through all topology*yml
# files, run transformation on them, and write the results into
# exp-topology*yml files (expected results)
#
for file in integration/${1:-*}.yml integration/*/${1:-*}.yml; do
  ../netlab create -o none -d none $file 2>/dev/null || (
    echo "Errors found in $file"
    echo "========================================="
    ../netlab create -o none -d none $file 
    echo ""
  )
done
