FROM fedora

WORKDIR /build
COPY . .

RUN echo -e "deltarpm=0\ninstall_weak_deps=0\ntsflags=nodocs" >> /etc/dnf/dnf.conf

# Temporary workaround until fedora:rawhide image is updated with up-to-date
# fedora-repos package.
RUN curl -O https://pagure.io/fedora-repos/raw/master/f/RPM-GPG-KEY-fedora-28-primary
RUN mv RPM-GPG-KEY-fedora-28-primary /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-28-x86_64
RUN rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-28-x86_64

RUN dnf -y update
RUN dnf -y install \
  # RPM packages for installing.
  rpm-libs \
  # rpm.pc used for "python setup.py build".
  rpm-devel \
  redhat-rpm-config \
  gcc \
  python3-devel \
  # python2-devel is not available on f25.
  python-devel \
  /usr/bin/python3.6 \
  /usr/bin/python3.5 \
  /usr/bin/python2.7 \
  # Used to get the rpm-python by git commmand,
  # if a target rpm archive URL is not found on the server.
  /usr/bin/git \
  # RPM packages for testing.
  # Used in scripts/lint_bash.sh
  which \
  # Used in scripts/lint_bash.sh
  /usr/bin/find \
  # Used in scripts/lint_bash.sh
  ShellCheck \
  && dnf clean all
RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip setuptools
RUN python3 -m pip install tox

# fedora:25, 26 tox is installed to /usr/bin/tox
# fedora:rawhide tox is installed to /usr/local/bin/tox
CMD ["tox"]
