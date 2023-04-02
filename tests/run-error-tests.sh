#!/bin/bash
#
# Run error tests in "display errors" mode to check netlab
# error messages
#
for file in errors/${1:-*}.yml; do
  echo ""
  echo "$file"
  echo "========================================="
  ../netlab create -o none $file
done
