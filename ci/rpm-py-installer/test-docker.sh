#!/bin/bash

set -ex

TOP_DIR="$(dirname "${0}")/../.."
cd "${TOP_DIR}/ci/rpm-py-installer"

docker build -t rpm-py-installer .
docker run -t rpm-py-installer
