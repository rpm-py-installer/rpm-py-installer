FROM fedora:26

RUN echo -e "deltarpm=0\ninstall_weak_deps=0\ntsflags=nodocs" >> /etc/dnf/dnf.conf
RUN dnf -y update
# python2-pip is not available on F25.
RUN dnf -y install \
  python2 \
  python2-devel \
  python3 \
  python3-devel \
  python-pip \
  python3-pip \
  git \
  findutils \
  gcc \
  make \
  zlib-devel \
  bzip2-devel \
  readline-devel \
  sqlite-devel \
  openssl-devel \
  && dnf clean all

# Install pyenv
# https://github.com/pyenv/pyenv
ENV HOME "/root"
RUN git clone https://github.com/pyenv/pyenv.git "${HOME}/.pyenv"
ENV PYENV_ROOT "${HOME}/.pyenv"
ENV PATH "${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"
RUN pyenv --version
RUN pyenv install 3.6.2
RUN pyenv install 3.5.3
RUN pyenv install 2.7.13
RUN pyenv rehash

COPY entry.sh "${HOME}/entry.sh"
ENTRYPOINT ["/root/entry.sh"]
