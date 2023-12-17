#!/bin/bash
#
# Create the error test cases -- capture printout generated
# on STDERR into a file that will be used in the test harness
# to validate the error handling hasn't been broken.
#
for file in errors/${1:-*}.yml; do
  echo Generating error outputs for $file into ${file%.yml}.log
  ../netlab create $file -o none --test errors 2>${file%.yml}.log
done
