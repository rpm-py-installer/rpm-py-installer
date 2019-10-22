SERVICE ?= fedora_rawhide
DOCKER ?= podman
CWD = $(shell pwd)

default : build
.PHONY : default

# Ex. make build SERVICE=fedora28
build :
	$(DOCKER)-compose build $(SERVICE)
.PHONY : build

# Ex. make test SERVICE=fedora28
test :
	$(DOCKER)-compose run --rm -v "$(CWD):/work" -w /work $(SERVICE)
.PHONY : test

# Ex. make login SERVICE=fedora28
login :
	"$(DOCKER)" run -v "$(CWD):/work" -w /work -it rpm-py-installer_$(SERVICE) bash
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
	$(DOCKER)-compose run --rm $@
.PHONY : qemu

clean :
	"$(DOCKER)" system prune -a -f
.PHONY : clean
