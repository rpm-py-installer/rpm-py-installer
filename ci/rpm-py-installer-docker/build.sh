#!/bin/bash

set -ex

docker build -t rpm-py-installer-docker .
docker tag rpm-py-installer-docker docker.io/junaruga/rpm-py-installer-docker:26
docker push docker.io/junaruga/rpm-py-installer-docker:26
