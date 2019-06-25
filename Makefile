SERVICE ?= fedora_rawhide
DOCKER = docker
QEMU_SUDO =

ifeq ($(DOCKER), podman)
	QEMU_SUDO = sudo
endif

default : build
.PHONY : default

# Ex. make build SERVICE=fedora28
build :
	scripts/container-compose.py $@ $(SERVICE)
.PHONY : build

# Ex. make test SERVICE=fedora28
test :
	scripts/container-compose.py $@ $(SERVICE)
.PHONY : test

# Ex. make login SERVICE=fedora28
login :
	scripts/container-compose.py $@ $(SERVICE)
.PHONY : login

build-no-volume :
	"$(DOCKER)" build --rm \
		-t rpm-py-installer_$(SERVICE) \
		-f ci/Dockerfile-fedora \
		--build-arg CONTAINER_IMAGE=$(CONTAINER_IMAGE) \
		.
	"$(DOCKER)" build --rm \
		-t rpm-py-installer_$(SERVICE)_test \
		-f ci/Dockerfile-test \
		--build-arg CONTAINER_IMAGE=rpm-py-installer_$(SERVICE) \
		.
.PHONY : build-no-volume

test-no-volume :
	"$(DOCKER)" run --rm \
		-t \
		-e TOXENV=$(TOXENV) \
		rpm-py-installer_$(SERVICE)_test \
		tox
.PHONY : test-no-volume

no-network-test :
	pytest -m 'not network'
.PHONY : no-network-test

qemu :
	$(QEMU_SUDO) "$(DOCKER)" run --rm --privileged multiarch/qemu-user-static:register --reset
.PHONY : qemu

clean :
	"$(DOCKER)" system prune -a -f
.PHONY : clean
