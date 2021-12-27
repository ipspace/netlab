#!/bin/bash
PYTHONPATH="../" python3 -m pytest -vvv
cd ..; python3 -m mypy --no-incremental -p netsim
