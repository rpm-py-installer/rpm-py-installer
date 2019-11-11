#!/bin/bash

set -euox pipefail

tox

if echo "${TOXENV}"|grep -q cov; then
    . /etc/os-release
    bash <(curl -s https://codecov.io/bash) -e "${ID}" || \
        echo "Codecov did not collect coverage reports"
fi
