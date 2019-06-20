"""
Tests for integration executed by CI.

"""

import sys

import pytest


@pytest.mark.integration
@pytest.mark.parametrize('python_path', (
    '/usr/bin/python3', '/usr/bin/python')
)
@pytest.mark.skipif(not pytest.helpers.is_root_user(),
                    reason='needs root authority.')
def test_install_failed_on_sys_python(install_script_path, python_path):
    # Case 1: rpm-py is installed on system Python.
    # Check rpm binding has already been installed before test.
    is_installed = _is_rpm_py_installed(python_path)
    if is_installed:
        # Check the install is skipped successfully.
        is_ok = _run_install_script(python_path, install_script_path)
        assert is_ok

        is_installed = _is_rpm_py_installed(python_path)
        assert is_installed

    # Case 2: rpm-py is not installed on system Python.
    _uninstall_rpm_py(python_path)

    is_installed = _is_rpm_py_installed(python_path)
    assert not is_installed

    is_ok = _run_install_script(python_path, install_script_path)
    assert not is_ok

    is_installed = _is_rpm_py_installed(python_path)
    assert not is_installed


# This integration test is run as a unit test.
# Because it works on user's environment. And not so costy.
# @pytest.mark.integration
@pytest.mark.network
@pytest.mark.parametrize('env', [
    {},
    {
        'RPM_PY_INSTALL_BIN': 'true',
        'RPM_PY_VERBOSE': 'true',
    },
], ids=[
    'No env variables',
    'RPM_PY_INSTALL_BIN: true',
])
def test_install_and_uninstall_are_ok_on_non_sys_python(
    install_script_path, env
):
    if 'RPM_PY_INSTALL_BIN' in env and env['RPM_PY_INSTALL_BIN'] == 'true' \
       and sys.version_info >= (3, 0) and sys.version_info < (3, 6):
        message = (
            'Installation from RPM Python binding binary package '
            'does not work on Python 3 <= 3.5.'
        )
        pytest.skip(message)

    _assert_install_and_uninstall(install_script_path, **env)


@pytest.mark.network
# This integration test is run as a unit test.
# rpm-build-libs might be always installed,
# Because when running "dnf remove rpm-build-libs", "dnf" itself was removed.
@pytest.mark.parametrize('is_rpm_devel, is_downloadable, is_rpm_build_libs', [
    (False, True, True),
    (True, False, True),
], ids=[
    'rpm-devel not installed, RPM package downloadable',
    'rpm-devel installed',
])
@pytest.mark.skipif(not pytest.helpers.is_root_user(),
                    reason='needs root authority.')
@pytest.mark.skipif(pytest.helpers.helper_is_debian(),
                    reason='Only Linux Fedora.')
def test_install_and_uninstall_are_ok_on_sys_status(
    install_script_path, is_dnf, pkg_cmd,
    is_rpm_devel, is_downloadable, is_rpm_build_libs,
    has_rpm_setup_py_in
):
    if not has_rpm_setup_py_in and not is_downloadable:
        pytest.skip('install without setup.py.in should be downlodable.')

    if is_rpm_devel:
        _run_cmd('{0} install rpm-devel'.format(pkg_cmd))
    else:
        _run_cmd('{0} remove rpm-devel popt-devel'.format(pkg_cmd))

    if is_downloadable:
        _install_rpm_download_utility(is_dnf, pkg_cmd)
    else:
        _uninstall_rpm_download_utility(is_dnf, pkg_cmd)

    try:
        _assert_install_and_uninstall(install_script_path)
    finally:
        try:
            # Reset as default system status.
            _run_cmd('{0} remove rpm-devel popt-devel'.format(pkg_cmd))
            _install_rpm_download_utility(is_dnf, pkg_cmd)
        except Exception:
            pass

    assert True


def _assert_install_and_uninstall(install_script_path, **env):
    try:
        python_path = sys.executable

        # Initilize environment.
        _uninstall_rpm_py(python_path)

        # Run the install script.
        script_env = {
            'RPM_PY_VERBOSE': 'true',
            'RPM_PY_WORK_DIR_REMOVED': 'true',
        }
        script_env.update(env)
        is_ok = _run_install_script(python_path,
                                    install_script_path, **script_env)
        assert is_ok

        # Installed successfully?
        is_installed = _is_rpm_py_installed(python_path)
        assert is_installed

        # Run RPM Python binding.
        assert _run_rpm_py(python_path)

        # Uninstalled successfully?
        was_uninstalled = _uninstall_rpm_py(python_path)
        assert was_uninstalled
    except AssertionError as e:
        # Remove installed RPM Python binding.
        # That causes next test case's error.
        try:
            _uninstall_rpm_py(python_path)
        except Exception:
            pass
        raise e


def _run_install_script(python_path, install_script_path, **env):
    def append_equal(tup):
        return '{0}={1}'.format(tup[0], tup[1])

    env_str = ''
    if env:
        env_str = ' '.join(map(append_equal, env.items()))
        env_str += ' '

    cmd = '{0}{1} {2}'.format(env_str, python_path, install_script_path)
    return _run_cmd(cmd)


def _is_rpm_py_installed(python_path):
    pip_cmd = _get_pip_cmd(python_path)
    cmd = '{0} list | grep -E "^rpm(-python)? "'.format(pip_cmd)
    is_installed = _run_cmd(cmd)
    if not is_installed:
        script = '''
import os
import shutil
import sys
from distutils.sysconfig import get_python_lib

lib_dirs = []
lib_dirs.append(get_python_lib())
lib_dirs.append(get_python_lib(plat_specific=True))
is_installed = False
for lib_dir in lib_dirs:
    init_py = os.path.join(lib_dir, 'rpm', '__init__.py')
    if os.path.isfile(init_py):
        is_installed = True
        print('__init__.py {0} exists.'.format(init_py))
        break
if not is_installed:
    sys.exit('__init__.py does not exist.')
'''
        cmd = '{0} -c "{1}"'.format(python_path, script)
        is_installed = _run_cmd(cmd)

    return is_installed


def _uninstall_rpm_py(python_path):
    was_uninstalled = False
    pip_cmd = _get_pip_cmd(python_path)
    for package_name in ('rpm-python', 'rpm'):
        cmd = '{0} uninstall -y {1}'.format(pip_cmd, package_name)
        if _run_cmd(cmd):
            was_uninstalled = True
            break

    # Old version "pip uninstall" returns the exit status: 0
    # when the package does not exist.
    # pip >= 10.0.0 can not uninstall a package installed by distutils.
    # https://github.com/pypa/pip/commit/fabb739
    script = '''
import glob
import os
import shutil
import sys
from distutils.sysconfig import get_python_lib

lib_dirs = []
if sys.version_info >= (3, 2):
    import site
    if hasattr(site, 'getsitepackages'):
        lib_dirs = site.getsitepackages()

lib_dirs.append(get_python_lib())
lib_dirs.append(get_python_lib(plat_specific=True))
for lib_dir in lib_dirs:
    rpm_dir = os.path.join(lib_dir, 'rpm')
    if os.path.isdir(rpm_dir):
        shutil.rmtree(rpm_dir)
        print('rpm_dir: {0} was removed.'.format(rpm_dir))
    egg_info_files = glob.glob(lib_dir + '/rpm*.egg-info')
    for egg_info_file in egg_info_files:
        if os.path.isfile(egg_info_file):
            os.remove(egg_info_file)
            print('egg_info_file: {0} was removed.'.format(egg_info_file))
'''
    cmd = '{0} -c "{1}"'.format(python_path, script)
    if _run_cmd(cmd):
        was_uninstalled = True

    return was_uninstalled


# See install.py Python _get_pip_cmd.
def _get_pip_cmd(python_path):
    if ((sys.version_info >= (2, 7, 9) and sys.version_info < (2, 8))
       or sys.version_info >= (3, 4)):
        pip_cmd = '{0} -m pip'.format(python_path)
    else:
        pip_cmd = 'pip'
    return pip_cmd


def _run_rpm_py(python_path):
    script = '''
import rpm
try:
    rpm.spec('tests/fixtures/hello.spec')
    print(rpm.expandMacro('%name'))
except AttributeError as e:
    # Observed the error on rpm-python 4.11.1 and Python 3.4.
    print('WARN: error at checking script: ' + str(e))
    print(rpm.__version__)
'''
    cmd = '{0} -c "{1}"'.format(python_path, script)
    return _run_cmd(cmd)


def _install_rpm_download_utility(is_dnf, pkg_cmd):
    if is_dnf:
        _run_cmd("{0} install 'dnf-command(download)'".format(pkg_cmd))
    else:
        # Install yumdownloader
        _run_cmd('{0} install /usr/bin/yumdownloader'.format(pkg_cmd))


def _uninstall_rpm_download_utility(is_dnf, pkg_cmd):
    if is_dnf:
        _run_cmd('{0} remove dnf-plugins-core'.format(pkg_cmd))
    else:
        _run_cmd('{0} remove /usr/bin/yumdownloader'.format(pkg_cmd))


def _run_cmd(cmd):
    return pytest.helpers.run_cmd(cmd)
