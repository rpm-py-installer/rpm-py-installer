# Arguments
DOCKER ?= podman
# Use the container engine's volume bind mount?
# true: It synchronizes the source between host and container.
#       It's good in case of developing, modifying the code on host, testing in container.
# false: It's good to use on CIs that do not support the volume mount.
DOCKER_VOLUME ?= true
DOCKERFILE ?= ci/Dockerfile-fedora
# Container image
IMAGE ?= fedora:rawhide
TOXENV ?= py3-cov
TEST_LINT ?= false
TEST_CMD ?= tox

TAG = rpm-py-installer_$(IMAGE)
CWD = $(shell pwd)

default : build
.PHONY : default

# Ex. make build IMAGE=fedora:28
build : build-volume-$(DOCKER_VOLUME)
.PHONY : build

# Ex. make test IMAGE=fedora:28 TOXENV=py3
test : test-volume-$(DOCKER_VOLUME)
.PHONY : test

build-volume-true :
	"$(DOCKER)" build --rm -t "$(TAG)" -f "$(DOCKERFILE)" \
		--build-arg CONTAINER_IMAGE=$(IMAGE) \
		--build-arg LINT="$(TEST_LINT)" \
		.
.PHONY : build-volume-true

test-volume-true :
	"$(DOCKER)" run --rm -t -v "$(CWD):/work:Z" -w /work -e TOXENV="${TOXENV}" \
		"$(TAG)" "$(TEST_CMD)"
.PHONY : test-volume-true

# Test on no network environment for the downstream build environment.
test-no-network :
	"$(DOCKER)" run -t --rm -v "$(CWD):/work:Z" -w /work --network=none \
		"$(TAG)" pytest -m no_network
.PHONY : test-no-network

# Ex. make login IMAGE=fedora:28
login :
	"$(DOCKER)" run -t -v "$(CWD):/work:Z" -w /work -it $(TAG) bash
.PHONY : login

# Ex. make build-volume-false IMAGE=fedora:28
build-volume-false :
	"$(DOCKER)" build --rm \
		-t $(TAG)_tmp \
		-f "$(DOCKERFILE)" \
		--build-arg CONTAINER_IMAGE=$(IMAGE) \
		.
	"$(DOCKER)" build --rm \
		-t $(TAG) \
		-f ci/Dockerfile-test \
		--build-arg CONTAINER_IMAGE=$(TAG)_tmp \
		.
.PHONY : build-volume-false

# Ex. make test-volume-false IMAGE=fedora:28 TOXENV=py3
test-volume-false :
	"$(DOCKER)" run --rm \
		-t \
		-e TOXENV=$(TOXENV) \
		$(TAG) \
		$(TEST_CMD)
.PHONY : test-volume-false

# Install /proc/sys/fs/binfmt_misc/qemu-$arch files on host to run multiple
# CPU architectures containers on QEMU.
# https://github.com/multiarch/qemu-user-static
qemu :
	"$(DOCKER)" run --rm -t --privileged multiarch/qemu-user-static --reset -p yes
.PHONY : qemu

clean : clean-files clean-containers
.PHONY : clean

clean-files :
	rm -rf .pytest_cache/
	rm -rf .tox/
	find . -type f -a -name "*.pyc" -delete
	find . -type d -a -name "__pycache__" -delete
.PHONY : clean-files

clean-containers :
	"$(DOCKER)" system prune -a -f
.PHONY : clean-containers
