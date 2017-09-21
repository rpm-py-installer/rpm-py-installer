"""
Tests for integration executed by CI.

"""

import os
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
        exit_status = _run_install_script(python_path, install_script_path)
        assert exit_status == 0

        is_installed = _is_rpm_py_installed(python_path)
        assert is_installed

    # Case 2: rpm-py is not installed on system Python.
    _uninstall_rpm_py(python_path)

    exit_status = _run_install_script(python_path, install_script_path)
    assert exit_status != 0

    is_installed = _is_rpm_py_installed(python_path)
    assert not is_installed


# Only this integration test is run as a basic test.
# Because it works on user's environment. And not so costy.
# @pytest.mark.integration
def test_install_and_uninstall_are_ok_on_non_sys_python(install_script_path):
    python_path = sys.executable
    exit_status = _run_install_script(python_path, install_script_path,
                                      VERBOSE='false',
                                      WORK_DIR_REMOVED='true')
    assert exit_status == 0

    is_installed = _is_rpm_py_installed(python_path)
    assert is_installed

    assert _run_rpm_py(python_path)

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
    print('CMD: {0}'.format(cmd))
    exit_status = os.system(cmd)
    return exit_status


def _is_rpm_py_installed(python_path):
    cmd = '{0} -m pip list | grep -E "^rpm(-python)? "'.format(python_path)
    exit_status = os.system(cmd)
    return (exit_status == 0)


def _uninstall_rpm_py(python_path):
    was_uninstalled = False
    for package_name in ('rpm-python', 'rpm'):
        cmd = '{0} -m pip uninstall -y {1}'.format(python_path, package_name)
        exit_status = os.system(cmd)
        if exit_status == 0:
            was_uninstalled = True
            break
    return was_uninstalled


def _run_rpm_py(python_path):
    script = '''
import rpm
rpm.spec('tests/fixtures/hello.spec')
print(rpm.expandMacro('%name'))
'''
    cmd = '{0} -c "{1}"'.format(python_path, script)
    exit_status = os.system(cmd)
    return (exit_status == 0)
