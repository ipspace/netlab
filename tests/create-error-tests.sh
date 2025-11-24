#!/usr/bin/env bash
#
# Create the error test cases -- capture printout generated
# on STDERR into a file that will be used in the test harness
# to validate the error handling hasn't been broken.
#
ERR_PATH="errors"

# Check for "coverage" first
if [[ "$1" == "coverage" ]]; then
    echo "Creating a code coverage error test"
    ERR_PATH="coverage/errors"
    shift
fi

# If no args left, default to "*"
if [[ $# -eq 0 ]]; then
    set -- "*"
fi

for arg in "$@"; do
  for file in ${ERR_PATH}/${arg}.yml; do
    echo Generating error outputs for $file into ${file%.yml}.log
    ../netlab create $file -o none --test errors 2>${file%.yml}.log
  done
done
