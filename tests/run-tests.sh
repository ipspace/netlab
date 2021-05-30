#!/bin/bash
PYTHONPATH="../" pytest
cd ..; mypy -p netsim
