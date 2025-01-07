#!/bin/bash
#
# Run transformation code on integration tests for an additional
# verification before merging pull requests
#
for file in integration/**/[0-9]*.yml platform-integration/**/[0-9]*.yml; do
  ../netlab create -o none -d none $file 2>/dev/null || (
    echo "Errors found in $file"
    echo "========================================="
    ../netlab create -o none -d none $file 
    echo ""
    exit 1
  ) || err_cnt=$((err_cnt + 1))
done
if [ "$err_cnt" -ne "0" ]; then
  echo "Found $err_cnt errors"
fi
exit $err_cnt
