#!/bin/sh

TOP_DIR="$(dirname "${0}")/.."
INSTALL_FILE="${TOP_DIR}/install"

echo 'System Python3'
PYTHON=/usr/bin/python3 bash "${INSTALL_FILE}" || echo "OK"

echo 'System Python2'
PYTHON=/usr/bin/python bash "${INSTALL_FILE}" || echo "OK"

PY_VERSIONS="
    3.6.2
    3.5.3
    2.7.13
"
for VERSION in ${PY_VERSIONS}; do
    echo "Python: ${VERSION}"
    pyenv global "${VERSION}"
    # Set PYTHON=python because default PYTHON: python3 is not available
    # on pyenv Python 2 environment.
    PYTHON=python bash "${INSTALL_FILE}"
    RPM_PYTHON=$(pip list | grep ^rpm | cut -d' ' -f 1)
    pip uninstall -y "${RPM_PYTHON}"
done
