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

    is_ok = _run_install_script(python_path, install_script_path)
    assert not is_ok

    is_installed = _is_rpm_py_installed(python_path)
    assert not is_installed


# This integration test is run as a unit test.
# Because it works on user's environment. And not so costy.
# @pytest.mark.integration
def test_install_and_uninstall_are_ok_on_non_sys_python(install_script_path):
    _assert_install_and_uninstall(install_script_path)


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
def test_install_and_uninstall_are_ok_on_sys_status(
    install_script_path, is_dnf, pkg_cmd,
    is_rpm_devel, is_downloadable, is_rpm_build_libs
):
    if is_rpm_devel:
        _run_cmd('{0} -y install rpm-devel'.format(pkg_cmd))
    else:
        _run_cmd('{0} -y remove rpm-devel popt-devel'.format(pkg_cmd))

    if is_downloadable:
        _install_rpm_download_utility(is_dnf)
    else:
        _uninstall_rpm_download_utility(is_dnf)

    # if is_rpm_build_libs:
    #     _run_cmd('{0} -y install rpm-build-libs'.format(pkg_cmd))
    # else:
    #     _run_cmd('{0} -y remove rpm-build-libs'.format(pkg_cmd))

    try:
        _assert_install_and_uninstall(install_script_path)
    finally:
        try:
            # Reset as default system status.
            _run_cmd('{0} -y remove rpm-devel popt-devel'.format(pkg_cmd))
            _install_rpm_download_utility(is_dnf)
            # _run_cmd('{0} -y install rpm-build-libs'.format(pkg_cmd))
        except Exception:
            pass

    assert True


def _assert_install_and_uninstall(install_script_path):
    python_path = sys.executable

    # Initilize environment.
    _uninstall_rpm_py(python_path)

    # Run the install script.
    is_ok = _run_install_script(python_path, install_script_path,
                                RPM_PY_VERBOSE='true',
                                RPM_PY_WORK_DIR_REMOVED='true')
    assert is_ok

    # Installed successfully?
    is_installed = _is_rpm_py_installed(python_path)
    assert is_installed

    # Run RPM Python binding.
    assert _run_rpm_py(python_path)

    # Uninstalled successfully?
    was_uninstalled = _uninstall_rpm_py(python_path)
    assert was_uninstalled


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
    return _run_cmd(cmd)


def _uninstall_rpm_py(python_path):
    was_uninstalled = False
    pip_cmd = _get_pip_cmd(python_path)
    for package_name in ('rpm-python', 'rpm'):
        cmd = '{0} uninstall -y {1}'.format(pip_cmd, package_name)
        if _run_cmd(cmd):
            was_uninstalled = True
            break
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
rpm.spec('tests/fixtures/hello.spec')
print(rpm.expandMacro('%name'))
'''
    cmd = '{0} -c "{1}"'.format(python_path, script)
    return _run_cmd(cmd)


def _install_rpm_download_utility(is_dnf):
    if is_dnf:
        _run_cmd("dnf -y install 'dnf-command(download)'")
    else:
        # Install yumdownloader
        _run_cmd('yum -y install /usr/bin/yumdownloader')


def _uninstall_rpm_download_utility(is_dnf):
    if is_dnf:
        _run_cmd('dnf -y remove dnf-plugins-core')
    else:
        _run_cmd('yum -y remove /usr/bin/yumdownloader')


def _run_cmd(cmd):
    return pytest.helpers.run_cmd(cmd)
