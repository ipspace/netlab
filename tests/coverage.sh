#!/bin/bash
coverage erase
PYTHONPATH="../" coverage run --source ../netsim -m pytest -k 'coverage or error'
coverage html
