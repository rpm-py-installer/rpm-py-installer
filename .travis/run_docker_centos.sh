#!/bin/sh

docker pull docker.io/centos:7
docker tag docker.io/centos:7 centos:7
docker run -it centos:7
