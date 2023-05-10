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
                     SetupPy,
                     SuseRpm)

OS_RELEASE_FILE = '/etc/os-release'
REDHAT_RELEASE_FILE = '/etc/redhat-release'

install_path = os.path.abspath('install.py')
sys.path.insert(0, install_path)

pytest_plugins = ['helpers_namespace']

running_user = getpass.getuser()


@pytest.helpers.register
def cmd_stdout(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, _ = p.communicate()
    return out.decode().rstrip()


def _get_os_dict():
    names = ['ID', 'VERSION_ID']
    os_dict = {}
    for name in names:
        os_dict[name] = None
    if not os.path.isfile(OS_RELEASE_FILE):
        return os_dict

    for name in names:
        cmd = '. /etc/os-release && echo -n "${0}"'.format(name)
        os_dict[name] = cmd_stdout(cmd)

    return os_dict


_os_dict = _get_os_dict()
_is_dnf = True if os.system('dnf --version') == 0 else False
_is_debian = True if _os_dict['ID'] in ['debian', 'ubuntu'] else False
_is_fedora = _os_dict['ID'] == 'fedora'
# CentOS6 does not have /etc/os-release file. only has /etc/redhat-release.
# When the /etc/redhat-release exists, identify it as centos
# to run fedora base specific tests in test_install_fedora.py.
_is_centos = _os_dict['ID'] == 'centos' or \
  (not _os_dict['ID'] and os.path.isfile(REDHAT_RELEASE_FILE))
_is_suse = bool('opensuse' in _os_dict['ID']) or \
    bool('sles' in _os_dict['ID']) \
    if _os_dict['ID'] is not None \
    else False


def pytest_collection_modifyitems(items):
    def get_marker(item, marker):
        try:
            return item.get_closest_marker(marker)
        except AttributeError:
            return item.get_marker(marker)
    for item in items:
        if get_marker(item, 'integration') is not None:
            pass
        else:
            item.add_marker(pytest.mark.unit)
        if get_marker(item, 'network') is not None:
            pass
        else:
            item.add_marker(pytest.mark.no_network)


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
    return _is_fedora


@pytest.fixture
def is_centos():
    """Return if it is CentOS Linux."""
    return _is_centos


@pytest.fixture
def is_debian():
    """Return if it is Debian base Linux."""
    return _is_debian


@pytest.fixture
def is_suse():
    """Return if it is SUSE base Linux."""
    return _is_suse


@pytest.fixture
def os_version():
    """Return OS version ID."""
    # Ubuntu version ID is a decimal.
    return float(_os_dict['VERSION_ID']) \
        if _os_dict['VERSION_ID'] is not None else -1


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
        'https://raw.githubusercontent.com/rpm-py-installer/rpm-py-installer'
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
def helper_is_suse():
    """Return if this is a SUSE based Linux. """
    return _is_suse


@pytest.helpers.register
def helper_is_fedora_based():
    """Returns whether this is a Fedora/RHEL based Linux. """
    return _is_fedora or _is_centos


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


def get_rpm(is_debian, is_suse, rpm_path, **kwargs):
    rpm = None
    if is_debian:
        rpm = DebianRpm(rpm_path, **kwargs)
    elif is_suse:
        rpm = SuseRpm(rpm_path, **kwargs)
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
def sys_rpm(sys_rpm_path, is_debian, is_suse):
    return get_rpm(is_debian, is_suse, sys_rpm_path)


@pytest.fixture
def local_rpm(is_debian, is_suse):
    return get_rpm(is_debian, is_suse, '/usr/local/bin/rpm', check=False)


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
