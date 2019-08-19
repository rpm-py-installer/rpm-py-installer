"""Common functions and a list of pytest.fixture here."""

import copy
import getpass
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager

import pytest
from install import (Application,
                     DebianInstaller,
                     DebianRpm,
                     Downloader,
                     FedoraInstaller,
                     FedoraRpm,
                     Linux,
                     Python,
                     RpmPy,
                     RpmPyVersion,
                     SetupPy)

OS_RELEASE_FILE = '/etc/os-release'

install_path = os.path.abspath('install.py')
sys.path.insert(0, install_path)

pytest_plugins = ['helpers_namespace']

running_user = getpass.getuser()


def _get_os_id():
    os_id = None
    if not os.path.isfile(OS_RELEASE_FILE):
        return os_id

    with open(OS_RELEASE_FILE) as f_in:
        for line in f_in:
            match = re.search(r'^ID=[\'"]?(\w+)?[\'"]?$', line)
            if match:
                os_id = match.group(1)
                break

    return os_id


_os_id = _get_os_id()
_is_dnf = True if os.system('dnf --version') == 0 else False
_is_debian = True if _os_id in ['debian', 'ubuntu'] else False


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
def arch(is_fedora):
    """Return architecture."""
    os_arch = cmd_stdout('uname -m')
    if is_fedora:
        os_arch = cmd_stdout('rpm -q rpm --qf %{arch}')
    return os_arch


@pytest.fixture
def is_fedora():
    """Return if it is Fedora Linux."""
    return _os_id == 'fedora'


@pytest.fixture
def is_centos():
    """Return if it is CentOS Linux."""
    return _os_id == 'centos'


@pytest.fixture
def is_debian():
    """Return if it is Debian base Linux."""
    return _is_debian


@pytest.fixture
def rpm_version_info():
    p = subprocess.Popen(['rpm', '--version'], stdout=subprocess.PIPE)
    out = p.communicate()[0]
    out = out.decode()
    version_str = out.split()[2]
    version_info_list = re.findall(r'[0-9a-zA-Z]+', version_str)

    def convert_to_int(string):
        value = None
        if re.match(r'^\d+$', string):
            value = int(string)
        else:
            value = string
        return value

    version_info_list = [convert_to_int(s) for s in version_info_list]

    return tuple(version_info_list)


@pytest.fixture
def rpm_version_info_min_rpm_build_libs():
    return (4, 9)


@pytest.fixture
def rpm_version_info_min_setup_py_in():
    return (4, 10)


@pytest.fixture
def has_rpm_rpm_build_libs(
    rpm_version_info,
    rpm_version_info_min_rpm_build_libs
):
    return rpm_version_info >= rpm_version_info_min_rpm_build_libs


@pytest.fixture
def has_rpm_setup_py_in(
    rpm_version_info,
    rpm_version_info_min_setup_py_in
):
    return rpm_version_info >= rpm_version_info_min_setup_py_in


@pytest.fixture
def is_dnf():
    return _is_dnf


@pytest.fixture
def pkg_cmd(is_dnf, arch):
    cmd = 'dnf' if is_dnf else 'yum'
    cmd = '{0} -y'.format(cmd)
    if is_dnf:
        cmd = '{0} --forcearch {1}'.format(cmd, arch)
    return cmd


@pytest.fixture
def file_url():
    url = (
        'https://raw.githubusercontent.com/junaruga/rpm-py-installer'
        '/master/tests/fixtures/remote_file'
    )
    return url


@pytest.fixture
def archive_file_path_dicts():
    archive_dir = os.path.abspath('tests/fixtures/archive')

    path_dicts = {
        'tar.gz': {
            'valid': os.path.join(archive_dir, 'valid.tar.gz'),
            'invalid': os.path.join(archive_dir, 'invalid.tar.gz'),
         },
        'tar.bz2': {
            'valid': os.path.join(archive_dir, 'valid.tar.bz2'),
            'invalid': os.path.join(archive_dir, 'invalid.tar.bz2'),
        },
    }
    return path_dicts


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


@pytest.fixture
def os_release_dir():
    return os.path.abspath('tests/fixtures/os_release')


@pytest.helpers.register
def is_root_user():
    return running_user == 'root'


@pytest.helpers.register
def helper_is_debian():
    """Return if it is Debian base Linux. """
    # TODO: This method is duplicated with fixture: is_debian.
    return _is_debian


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


def helper_setup_py_path():
    # TODO: This method is duplicated with fixture: is_debian.
    return os.path.abspath('tests/fixtures/setup.py.in')


@pytest.helpers.register
@contextmanager
def work_dir_with_setup_py():
    path = helper_setup_py_path()
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


@pytest.helpers.register
def cmd_stdout(cmd):
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    out, _ = p.communicate()
    return out.decode().rstrip()


def get_rpm(is_debian, rpm_path, **kwargs):
    rpm = None
    if is_debian:
        rpm = DebianRpm(rpm_path, **kwargs)
    else:
        rpm = FedoraRpm(rpm_path, **kwargs)
    return rpm


@pytest.fixture
def sys_rpm_path():
    if os.path.isfile('/usr/bin/rpm'):
        return '/usr/bin/rpm'
    else:
        return '/bin/rpm'


@pytest.fixture
def sys_rpm(sys_rpm_path, is_debian):
    return get_rpm(is_debian, sys_rpm_path)


@pytest.fixture
def local_rpm(is_debian):
    return get_rpm(is_debian, '/usr/local/bin/rpm', check=False)


@pytest.fixture
def setup_py():
    rpm_py_version = RpmPyVersion('4.14.0-rc1')
    setup_py = SetupPy(rpm_py_version)
    # To update attribute.
    return copy.deepcopy(setup_py)


@pytest.fixture
def downloader():
    rpm_py_version = RpmPyVersion('4.14.0-rc1')
    downloader = Downloader(rpm_py_version)
    return downloader


@pytest.fixture
def installer(sys_rpm, is_debian):
    installer = None
    if is_debian:
        installer = DebianInstaller(RpmPyVersion('4.13.0'), Python(), sys_rpm)
    else:
        installer = FedoraInstaller(RpmPyVersion('4.13.0'), Python(), sys_rpm)
    return copy.deepcopy(installer)


@pytest.fixture
def rpm_py(sys_rpm_path):
    version_str = '4.13.0'
    python = Python()
    linux = Linux.get_instance(python=python, rpm_path=sys_rpm_path)
    return RpmPy(version_str, python, linux)


@pytest.fixture
def env():
    pass


@pytest.fixture
def app(env, monkeypatch):
    if env:
        if not isinstance(env, dict):
            raise ValueError('env: Invalid type: {0}'.format(type(env)))
        for key in env:
            monkeypatch.setenv(key, env[key])

    return copy.deepcopy(Application())
