#!/bin/bash

set -ex

RPM_VERSION=$(rpm --version | cut -d' ' -f 3)

WORK_DIR="$(pwd)/tmp/rpm-py-installer"
if [ -d "${WORK_DIR}" ]; then
    rm -rf "${WORK_DIR}"
fi
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

REPO_URL='https://github.com/rpm-software-management/rpm'
FILE_NAME="rpm-${RPM_VERSION}-release"
curl -L "${REPO_URL}/archive/${FILE_NAME}.tar.gz" | tar xz

cd "rpm-${FILE_NAME}/python"

sed -e 's/@PACKAGE_NAME@/rpm/g' \
    -e "s/@VERSION@/${RPM_VERSION}/g" \
    -e "s/@PACKAGE_BUGREPORT@/rpm-maint@lists.rpm.org/g" \
    setup.py.in \
    > setup.py

# If can not build, check below files.
# $ rpm -ql rpm-libs
# $ ls /usr/lib64/librpm*.so
# pip install -e .
python setup.py build
python setup.py install

pip list | grep rpm

python -c 'import rpm; print(rpm.__version__)'
