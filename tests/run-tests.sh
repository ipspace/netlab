#!/bin/bash
PYTHONPATH="../" python3 -m pytest
cd ..; python3 -m mypy --no-incremental -p netsim
