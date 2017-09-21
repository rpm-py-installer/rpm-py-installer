"""Common functions and a list of pytest.fixture here."""

import getpass
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

import pytest

install_path = os.path.abspath('install.py')
sys.path.insert(0, install_path)

pytest_plugins = ['helpers_namespace']

running_user = getpass.getuser()
_is_dnf = True if os.system('dnf --version') == 0 else False


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_marker('integration') is not None:
            pass
        else:
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def install_script_path():
    return install_path


@pytest.fixture
def is_dnf():
    return _is_dnf


@pytest.fixture
def pkg_cmd(is_dnf):
    return 'dnf' if is_dnf else 'yum'


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


@pytest.fixture
def rpm_files():
    rpm_dir = 'tests/fixtures/rpm'

    def add_abs_rpm_dir(file_name):
        return os.path.abspath(os.path.join(rpm_dir, file_name))

    files = list(map(add_abs_rpm_dir, os.listdir(rpm_dir)))

    return files


@pytest.fixture
def setup_py_path():
    return os.path.abspath('tests/fixtures/setup.py.in')


@pytest.helpers.register
def is_root_user():
    return running_user == 'root'


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
def work_dir_with_setup_py():
    path = setup_py_path()
    with work_dir():
        shutil.copy(path, '.')
        yield


@pytest.helpers.register
@contextmanager
def pushd(target_dir):
    current_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        yield
    finally:
        os.chdir(current_dir)


@pytest.helpers.register
def touch(file_path):
    f = None
    try:
        f = open(file_path, 'a')
    finally:
        f.close()


@pytest.helpers.register
def run_cmd(cmd):
    print('CMD: {0}'.format(cmd))
    exit_status = os.system(cmd)
    return (exit_status == 0)
