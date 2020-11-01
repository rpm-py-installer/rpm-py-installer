# Arguments
DOCKER ?= podman
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
build :
	"$(DOCKER)" build --rm -t "$(TAG)" -f "$(DOCKERFILE)" \
		--build-arg CONTAINER_IMAGE=$(IMAGE) \
		--build-arg LINT="$(TEST_LINT)" \
		.
.PHONY : build

# Ex. make test IMAGE=fedora:28 TOXENV=py3
test :
	"$(DOCKER)" run --rm -t -v "$(CWD):/work:Z" -w /work -e TOXENV="${TOXENV}" \
		"$(TAG)" "$(TEST_CMD)"
.PHONY : test

# Ex. make login IMAGE=fedora:28
login :
	"$(DOCKER)" run -t -v "$(CWD):/work:Z" -w /work -it $(TAG) bash
.PHONY : login

# Ex. make build-no-volume IMAGE=fedora:28
build-no-volume :
	"$(DOCKER)" build --rm \
		-t $(TAG) \
		-f ci/Dockerfile-fedora \
		--build-arg CONTAINER_IMAGE=$(IMAGE) \
		.
	"$(DOCKER)" build --rm \
		-t $(TAG)_test \
		-f ci/Dockerfile-test \
		--build-arg CONTAINER_IMAGE=$(TAG) \
		.
.PHONY : build-no-volume

# Ex. make test-no-volume IMAGE=fedora:28 TOXENV=py3
test-no-volume :
	"$(DOCKER)" run --rm \
		-t \
		-e TOXENV=$(TOXENV) \
		$(TAG)_test \
		$(TEST_CMD)
.PHONY : test-no-volume

# Test on no network environment for the downstream build environment.
no-network-test :
	"$(DOCKER)" run -t --rm -v "$(CWD):/work:Z" -w /work -e TOXENV="${TOXENV}" \
		--network=none \
		"$(TAG)" pytest -m no_network
.PHONY : no-network-test

qemu :
	"$(DOCKER)" run --rm -t --privileged multiarch/qemu-user-static --reset -p yes
.PHONY : qemu

clean :
	"$(DOCKER)" system prune -a -f
.PHONY : clean
