#!/bin/sh

set -ex

# See https://podman.io/getting-started/installation - Ubuntu
. /etc/os-release
echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | \
    sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/Release.key | \
    sudo apt-key add -
sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get -y install podman

# We need to register travis to allow subuid/gid for the rootless execution.
cat /etc/subuid
cat /etc/subgid
echo "travis:110000:65535" | sudo tee /etc/subuid
echo "travis:110000:65535" | sudo tee /etc/subgid

podman version
podman info --debug
