#!/bin/sh
# shellcheck disable=SC2039

set -xe

# X.Y.Z
PY_VERSION="${1}"
INSTALL_DIR="/usr/local/python-${PY_VERSION}"
PY_URL_PREFIX="https://www.python.org/ftp/python/${PY_VERSION}"
PY_FILE_NAME="Python-${PY_VERSION}.tgz"
PY_URL="${PY_URL_PREFIX}/${PY_FILE_NAME}"

# old version curl has an issue on CentOS5.
# curl: (35) error:1407742E:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert protocol version
curl -O "${PY_URL}"
tar xf "Python-${PY_VERSION}.tgz"
pushd "Python-${PY_VERSION}"
./configure --prefix "${INSTALL_DIR}" -q
make -j 4 -s
make install > /dev/null
popd

"${INSTALL_DIR}/bin/python" --version
