#!/bin/bash

set -ex

docker build -t rpm-py-installer .
docker run -t rpm-py-installer
