#!/bin/bash
DIRNAME=`dirname "$0"`
echo "Executing CI/CD tests in $DIRNAME"
cd "$DIRNAME"
PYTHONPATH="../" python3 -m pytest -vvv -k transformation_case
