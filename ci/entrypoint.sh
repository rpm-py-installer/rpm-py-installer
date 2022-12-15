#!/bin/bash

set -e

echo "TOXENV: ${TOXENV}"

if command -v pip > /dev/null; then
  set -x
  pip list
fi

exec $*
