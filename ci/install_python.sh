#!/bin/sh
# shellcheck disable=SC2039

set -e

# X.Y.Z
PY_VERSION="${1}"
INSTALL_DIR="/usr/local/python-${PY_VERSION}"
PY_URL_PREFIX="https://www.python.org/ftp/python/${PY_VERSION}"
PY_URL="${PY_URL_PREFIX}/Python-${PY_VERSION}.tgz"
(
    curl -sO "${PY_URL}"
    tar xf "Python-${PY_VERSION}.tgz"
    pushd "Python-${PY_VERSION}"
    ./configure --prefix "${INSTALL_DIR}"
    make -j 4
    make install
    popd
) > /dev/null
"${INSTALL_DIR}/bin/python" --version
