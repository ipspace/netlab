#!/bin/bash
#
. vars.sh
echo "Removing empty log files"
find . -name '*log' -empty -print -delete
echo
echo "Creating HTML reports"
create-reports.py --html
echo
echo "Submitting test results to GitHub"
git add .
git commit -m "${1:-Integration tests finished at $(date)}"
git push
