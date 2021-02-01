#!/bin/bash
coverage erase
PYTHONPATH="../lib/create-topology" coverage run --source ../lib -m pytest
coverage html
