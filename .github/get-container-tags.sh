#!/bin/bash
#
TAG=${1#release_}
XTAG=latest
if [[ $TAG == *"dev"* ]]; then
  XTAG=dev
  echo "PIP_OPTIONS=--pre"
else
  echo "PIP_OPTIONS="
fi
echo "IMAGE_TAG=$TAG,$XTAG"
