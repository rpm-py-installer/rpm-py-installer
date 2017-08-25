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


@pytest.mark.integration
def test_install_and_uninstall_are_ok_on_non_sys_python(install_script_path):
    python_path = sys.executable
    exit_status = _run_install_script(python_path, install_script_path)
    assert exit_status == 0

    is_installed = _is_rpm_py_installed(python_path)
    assert is_installed

    was_uninstalled = _uninstall_rpm_py(python_path)
    assert was_uninstalled


def _run_install_script(python_path, install_script_path):
    cmd = 'VERBOSE=true {0} {1}'.format(python_path, install_script_path)
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
