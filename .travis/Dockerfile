FROM fedora

WORKDIR /build
COPY . .

RUN echo -e "deltarpm=0\ninstall_weak_deps=0\ntsflags=nodocs" >> /etc/dnf/dnf.conf
RUN dnf -y update
# rpm-devel: rpm.pc used for "python setup.py build".
# which: Used in install.py, scripts/lint_bash.sh
# ShellCheck: Used in scripts/lint_bash.sh
# python2-devel is not available on f25.
RUN dnf -y install \
  rpm-libs \
  rpm-devel \
  redhat-rpm-config \
  gcc \
  python3-devel \
  python-devel \
  /usr/bin/python3.6 \
  /usr/bin/python3.5 \
  /usr/bin/python2.7 \
  which \
  ShellCheck \
  && dnf clean all

RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip setuptools
RUN python3 -m pip install tox

CMD ["/usr/bin/tox"]
