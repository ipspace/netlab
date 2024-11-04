#!/bin/bash
#
# Using the test cases in toplogy/input/**yml, generate config outputs to test the device templates
#
OUT=run-config-tests.log
ERR=run-config-tests.err.log
set +e
for file in topology/input/${1:-*}.yml; do
  echo "Creating configs based on $file..."
  echo "Creating configs based on $file..." >> $OUT
  echo "Creating configs based on $file..." >> $ERR
  PYTHONPATH="../" netlab create $file>>$OUT 2>>$ERR
  PYTHONPATH="../" netlab initial -o test_configs >>$OUT 2>>$ERR
  PYTHONPATH="../" netlab down --cleanup >>$OUT 2>>$ERR
  echo "DONE creating configs based on $file..." >> $OUT
done
#
# Remove files when done
#
rm -fr test_configs
