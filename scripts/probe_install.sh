#!/bin/sh
# shellcheck disable=SC2039
#
# This script is to probe and investigate the RPM Python binding's build
# and install simply.
# It is not used in production.
# It is run in a upstream rpm/python directory.
#
# For example,
# $ cd ~/git/rpm/python
# $ python3 -m venv ./venv
# $ source venv/bin/activate
# (venv) $ ~/git/rpm-py-installer/scripts/probe_install.sh

set -ex

PYTHON=python
RPM_PY_VERSION="$(rpm --version | cut -d' ' -f 3)"

if rpm --query rpm-devel --quiet; then
    echo "rpm-devel installed. Remove it to run this script correctly." 1>&2
    exit 1
fi

# rpm-libs
if ! rpm --query rpm-libs --quiet; then
    echo "rpm-devel not installed. Install it." 1>&2
    exit 1
fi
# rpm-build-libs (added newly from rpm 4.9.0-beta1.
if ! rpm --query rpm-build-libs --quiet; then
    echo "rpm-devel not installed. Install it." 1>&2
    exit 1
fi


LIB_RPM_SO_PATH=$(rpm -ql rpm-libs | grep librpm.so | head -1 \
    | sed -e 's/[.0-9]*$//')
RPM_LIB_DIR=$(dirname "${LIB_RPM_SO_PATH}")

git checkout "rpm-${RPM_PY_VERSION}-release"

"${PYTHON}" -m pip list

# Normally setup.py and rpm.pc are created in "./configure" process.
sed -e 's/@PACKAGE_NAME@/rpm/g' \
    -e "s/@VERSION@/${RPM_PY_VERSION}/g" \
    -e "s/@PACKAGE_BUGREPORT@/rpm-maint@lists.rpm.org/g" \
    setup.py.in \
    > setup.py

# Replace or create include_dirs, library_dirs, libraries, runtime_library_dirs
sed -i "s|pkgconfig('--cflags')|\['/usr/include'\]|" setup.py
sed -i "s|pkgconfig('--libs')|\['${RPM_LIB_DIR}', 'rpm', 'rpmio'\]|" setup.py

pushd ..

# Normally rpm.pc is created in "make" process.
# The logic is in "configure" script.
# Regarding replaced values, see built rpm.pc on Fedora rpm package.
# shellcheck disable=SC2016
# Note @libdir@ has flexible value for RPM versions
# sed -e 's|@prefix@|/usr|g' \
#     -e 's|@exec_prefix@|${prefix}|g' \
#     -e "s|@libdir@|${RPM_LIB_DIR}|g" \
#     -e 's|@includedir@|${prefix}/include|g' \
#     -e 's|@RPMCONFIGDIR@|/usr/lib/rpm|g' \
#     -e "s|@VERSION@|${RPM_PY_VERSION}|g" \
#     -e 's|@ZSTD_REQUIRES@||g' \
#     -e 's|@LMDB_REQUIRES@||g' \
#     -e 's|@WITH_LZMA_LIB@|-llzma|g' \
#     -e 's|@WITH_DB_LIB@|-ldb|g' \
#     -e 's|@WITH_BZ2_LIB@|-lbz2|g' \
#     -e 's|@WITH_ZLIB_LIB@|-lz|g' \
#     -e 's|@WITH_BEECRYPT_LIB@||g' \
#     -e 's|@WITH_NSS_LIB@|-lnss3|g' \
#     -e 's|@LUA_LIBS@|-llua -lm -ldl|g' \
#     rpm.pc.in \
#     > rpm.pc

INCLUDE_RPM_DIR='include/rpm'
if [ -d "${INCLUDE_RPM_DIR}" ]; then
    rm -rf "${INCLUDE_RPM_DIR}"
fi
mkdir -p "${INCLUDE_RPM_DIR}"

HEADER_DIRS="
    rpmio
    lib
    build
    sign
"
for HEADER_DIR in ${HEADER_DIRS}; do
    find "${HEADER_DIR}" -name "*.h" | while read -r HEAD_FILE; do
        DST_FILE=$(echo "${HEAD_FILE}" | sed "s|${HEADER_DIR}/||")
        DST_FILE="${INCLUDE_RPM_DIR}/${DST_FILE}"
        DST_DIR="$(dirname "${DST_FILE}")"
        if [ ! -d "${DST_DIR}" ]; then
            mkdir -p "${DST_DIR}"
        fi

        cp -p "${HEAD_FILE}" "${DST_FILE}"
    done
done

BUILD_LIB_DIRS="
    rpmio/.libs
    lib/.libs
    build/.libs
    sign/.libs
"
for BUILD_LIB_DIR in ${BUILD_LIB_DIRS}; do
    if [ -d "${BUILD_LIB_DIR}" ]; then
        rm -rf "${BUILD_LIB_DIR}"
    fi
    mkdir -p "${BUILD_LIB_DIR}"
done


# rpm-libs
LIB_RPM_IO_PATH="$(find "${RPM_LIB_DIR}" -name "librpmio.so*" -a -type f)"
LIB_RPM_PATH="$(find "${RPM_LIB_DIR}" -name "librpm.so*" -a -type f)"

# rpm-build-libs
LIB_RPM_BUILD_PATH="$(find "${RPM_LIB_DIR}" -name "librpmbuild.so*" \
    -a -type f)"
LIB_RPM_SIGN_PATH="$(find "${RPM_LIB_DIR}" -name "librpmsign.so*" -a -type f)"

ln -s "${LIB_RPM_IO_PATH}" rpmio/.libs/librpmio.so
ln -s "${LIB_RPM_PATH}" lib/.libs/librpm.so
ln -s "${LIB_RPM_BUILD_PATH}" build/.libs/librpmbuild.so
ln -s "${LIB_RPM_SIGN_PATH}" sign/.libs/librpmsign.so

popd

"${PYTHON}" setup.py build
"${PYTHON}" setup.py install

"${PYTHON}" -m pip list

# Change directory from rpm/python
# to avoid load rpm/python/rpm/__init__.py wrongly,
# when doing "import rpm".
cd ..
"${PYTHON}" -c 'import rpm; print(rpm.__version__)'
