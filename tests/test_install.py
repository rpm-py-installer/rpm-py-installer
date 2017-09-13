"""
Tests for install.py

"""
import os
import re
import tempfile
from unittest import mock

import pytest

from install import (Application, ArchiveNotFoundError, Cmd, InstallError,
                     InstallSkipError, Log)


@pytest.fixture
def app():
    return Application()


@pytest.fixture
def app_with_env(env, monkeypatch):
    if not isinstance(env, dict):
        raise ValueError('env: Invalid type: {0}'.format(type(env)))
    for key in env:
        monkeypatch.setenv(key, env[key])
    return Application()


def test_cmd_sh_e_is_ok():
    stdout = Cmd.sh_e('pwd')
    assert not stdout


def test_cmd_sh_e_is_failed():
    with pytest.raises(InstallError):
        Cmd.sh_e('ls abcde')
    assert True


def test_cmd_sh_e_out_is_ok():
    stdout = Cmd.sh_e_out('pwd')
    assert stdout
    assert re.match('^.*\n$', stdout)


def test_cmd_cd_is_ok():
    with pytest.helpers.reset_dir():
        tmp_dir = tempfile.gettempdir()
        Cmd.cd(tmp_dir)
        cwd = os.getcwd()
        assert cwd == tmp_dir


@pytest.mark.parametrize('cmd', ['rpm'])
def test_cmd_which_is_ok(cmd):
    abs_path = Cmd.which(cmd)
    assert re.match('^/.*{0}$'.format(cmd), abs_path)


def test_cmd_curl_is_ok(file_url):
    with pytest.helpers.work_dir():
        assert Cmd.curl_remote_name(file_url)


def test_cmd_curl_is_failed(file_url):
    not_existed_file_url = file_url + '.dummy'
    with pytest.helpers.work_dir():
        with pytest.raises(ArchiveNotFoundError) as ei:
            Cmd.curl_remote_name(not_existed_file_url)
    assert re.match('^Download failed: .* HTTP Error 404: Not Found$',
                    str(ei.value))


def test_cmd_tar_xzf_is_ok(tar_gz_file_path):
    with pytest.helpers.work_dir():
        Cmd.tar_xzf(tar_gz_file_path)
        assert os.path.isdir('a')


def test_cmd_tar_xzf_is_failed(invalid_tar_gz_file_path):
    with pytest.helpers.work_dir():
        with pytest.raises(InstallError) as ei:
            Cmd.tar_xzf(invalid_tar_gz_file_path)
    assert re.match('^Extract failed: .* could not be opened successfully$',
                    str(ei.value))


def test_app_init(app):
    assert app
    assert app.verbose is False
    assert app.python_path
    assert 'bin/python' in app.python_path
    assert app.rpm_path
    assert 'rpm' in app.rpm_path
    assert app.rpm_py_version
    # Actual string is N.N.N.N or N.N.N.N-(rc|beta)N
    # Check verstion string roughly right now.
    assert re.match('^[\d.]+(-[a-z\d]+)?$', app.rpm_py_version)
    assert app.setup_py_optimized is True
    assert app.setup_py_opts == '-q'
    assert app.is_work_dir_removed is True


@pytest.mark.parametrize('env', [{'RPM': 'pwd'}])
def test_app_init_env_rpm(app_with_env):
    assert app_with_env
    assert re.match('^/.+/pwd$', app_with_env.rpm_path)


@pytest.mark.parametrize('env', [{'RPM_PY_VERSION': '1.2.3'}])
def test_app_init_env_rpm_py_version(app_with_env):
    assert app_with_env
    assert app_with_env.rpm_py_version == '1.2.3'


@pytest.mark.parametrize('env', [
    {'SETUP_PY_OPTM': 'true'},
    {'SETUP_PY_OPTM': 'false'},
])
def test_app_init_env_setup_py_optm(app_with_env, env):
    assert app_with_env
    value = True if env['SETUP_PY_OPTM'] == 'true' else False
    assert app_with_env.setup_py_optimized is value


@pytest.mark.parametrize('env', [{'VERBOSE': 'true'}])
def test_app_init_env_verbose(app_with_env):
    assert app_with_env
    assert app_with_env.verbose is True


@pytest.mark.parametrize('env', [
    {'WORK_DIR_REMOVED': 'true'},
    {'WORK_DIR_REMOVED': 'false'},
])
def test_app_init_env_work_dir_removed(app_with_env, env):
    assert app_with_env
    value = True if env['WORK_DIR_REMOVED'] == 'true' else False
    assert app_with_env.is_work_dir_removed is value


def test_verify_system_status_is_ok(app):
    app.verify_system_status()
    assert True


def test_verify_system_status_is_skipped_sys_python_and_rpm_py_installed(app):
    app.is_system_python = mock.MagicMock(return_value=True)
    app.is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.raises(InstallSkipError):
        app.verify_system_status()

    assert True


def test_verify_system_status_is_error_on_sys_py_and_rpm_py_not_installed(app):
    app.is_system_python = mock.MagicMock(return_value=True)
    app.is_python_binding_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app.verify_system_status()
    assert re.match('^RPM Python binding on system Python.*manually.$',
                    str(ei.value))


def test_verify_system_status_is_error_on_sys_rpm_and_missing_packages(app):
    app.is_system_rpm = mock.MagicMock(return_value=True)
    app.is_rpm_package_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app.verify_system_status()
    expected_message = (
        'Required RPM not installed: [rpm-libs, rpm-devel].\n'
        'Install it by "dnf install rpm-libs rpm-devel".\n'
    )
    assert expected_message == str(ei.value)


def test_is_rpm_package_installed_returns_true(app):
    with mock.patch.object(Cmd, 'sh_e'):
        assert app.is_rpm_package_installed('dummy')


def test_is_rpm_package_installed_returns_false(app):
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        mock_sh_e.side_effect = InstallError('test.')
        assert not app.is_rpm_package_installed('dummy')


@pytest.mark.parametrize('value_dict', [
    {
        'version': '4.13.0',
        'tag_names': [
            'rpm-4.13.0-release',
            'rpm-4.13.0',
        ],
    },
    {
        'version': '4.14.0-rc1',
        'tag_names': [
            'rpm-4.14.0-rc1',
            'rpm-4.14.0-rc1-release',
        ],
    },

])
def test_predict_candidate_git_tag_names_is_ok(app, value_dict):
    app.rpm_py_version = value_dict['version']
    tag_names = app.predict_candidate_git_tag_names()
    assert tag_names == value_dict['tag_names']


@mock.patch.object(Log, 'verbose', new=False)
def test_run_is_ok(app):
    app.is_work_dir_removed = True
    app.run()
    assert True


@mock.patch.object(Log, 'verbose', new=False)
@pytest.mark.parametrize('rpm_py_version',
                         ['4.13.0', '4.14.0-rc1'])
def test_run_is_ok_by_rpm_py_version(app, rpm_py_version):
    app.is_work_dir_removed = True
    app.rpm_py_version = rpm_py_version
    tag_names = app.predict_candidate_git_tag_names()
    top_dir_name = app.get_rpm_archive_top_dir_name(tag_names[0])

    def mock_download_and_expand_rpm_py(*args, **kwargs):
        rpm_py_dir = os.path.join(top_dir_name, 'python')
        os.makedirs(rpm_py_dir)
        return top_dir_name

    app.download_and_expand_rpm_py = mock_download_and_expand_rpm_py
    app.install_rpm_py = mock.MagicMock(return_value=True)
    app.is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.helpers.work_dir():
        app.run()
    assert True
