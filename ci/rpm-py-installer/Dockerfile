FROM junaruga/rpm-py-installer-docker:26

WORKDIR /build
COPY . .

RUN dnf -y update
# which: Used in install file.
# rpm-devel: For rpm.pc used for "python setup.py build".
RUN dnf -y install \
  which \
  rpm-devel \
  && dnf clean all

CMD ["./tests/test_install.sh"]
