#!/bin/bash
coverage erase
PYTHONPATH="../" coverage run --source ../netsim -m pytest
coverage html
