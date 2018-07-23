FROM fedora

ARG TOXENV

WORKDIR /build
COPY . .

RUN echo -e "deltarpm=0\ninstall_weak_deps=0\ntsflags=nodocs" >> /etc/dnf/dnf.conf

RUN dnf -y update
RUN dnf -y --allowerasing install \
  # -- RPM packages required for installing --
  rpm-libs \
  redhat-rpm-config \
  gcc \
  python3-devel \
  # python2-devel is not available on f25.
  python-devel \
  /usr/bin/python3.7 \
  /usr/bin/python3.6 \
  /usr/bin/python3.5 \
  /usr/bin/python2.7 \
  /usr/bin/python2.6 \
  # -- RPM packages required for a specified case --
  # Used to get the rpm-python by git commmand,
  # if a target rpm archive URL is not found on the server.
  /usr/bin/git \
  # rpm-build-libs or DNF download plugin is required for building.
  # rpm-build-libs might be always installed.
  rpm-build-libs \
  'dnf-command(download)' \
  # Used if downloading and extracting build dependency packages in installing.
  /usr/bin/cpio
  # -- RPM packages for testing --

RUN ./.travis/dnf_install_lint_pkgs.sh
RUN dnf clean all
RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip setuptools
RUN python3 -m pip install tox

# fedora:25, 26 tox is installed to /usr/bin/tox
# fedora:rawhide tox is installed to /usr/local/bin/tox
CMD ["tox"]
