"""Common functions and a list of pytest.fixture here."""

import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

import pytest

install_path = os.path.abspath('install.py')
sys.path.insert(0, install_path)

pytest_plugins = ['helpers_namespace']


@pytest.fixture
def install_script_path():
    return install_path


@pytest.fixture
def file_url():
    url = (
        'https://raw.githubusercontent.com/junaruga/rpm-py-installer'
        '/master/README.md'
    )
    return url


@pytest.fixture
def tar_gz_file_path():
    return os.path.abspath('tests/fixtures/valid.tar.gz')


@pytest.fixture
def invalid_tar_gz_file_path():
    return os.path.abspath('tests/fixtures/invalid.tar.gz')


@pytest.helpers.register
@contextmanager
def reset_dir():
    current_dir = os.getcwd()
    try:
        yield
    finally:
        os.chdir(current_dir)


@pytest.helpers.register
@contextmanager
def work_dir():
    with reset_dir():
        tmp_dir = tempfile.mkdtemp(suffix='-rpm-py-installer-test')
        os.chdir(tmp_dir)
        try:
            yield
        finally:
            shutil.rmtree(tmp_dir)


@pytest.helpers.register
@contextmanager
def pushd(target_dir):
    current_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        yield
    finally:
        os.chdir(current_dir)
