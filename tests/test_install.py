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
def env():
    pass


@pytest.fixture
def app(env, monkeypatch):
    if env:
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


@pytest.mark.parametrize('cmd', ['rpm', 'git'])
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
    assert app.git_branch is None
    assert app.setup_py_optimized is True
    assert app.setup_py_opts == '-q'
    assert app.is_work_dir_removed is True


@pytest.mark.parametrize('env', [{'RPM': 'pwd'}])
def test_app_init_env_rpm(app):
    assert app
    assert re.match('^/.+/pwd$', app.rpm_path)


@pytest.mark.parametrize('env', [{'RPM_PY_VERSION': '1.2.3'}])
def test_app_init_env_rpm_py_version(app):
    assert app
    assert app.rpm_py_version == '1.2.3'


@pytest.mark.parametrize('env', [{'GIT_BRANCH': 'master'}])
def test_app_init_env_git_branch(app):
    assert app
    assert app.git_branch == 'master'


@pytest.mark.parametrize('env', [
    {'SETUP_PY_OPTM': 'true'},
    {'SETUP_PY_OPTM': 'false'},
])
def test_app_init_env_setup_py_optm(app, env):
    assert app
    value = True if env['SETUP_PY_OPTM'] == 'true' else False
    assert app.setup_py_optimized is value


@pytest.mark.parametrize('env', [{'VERBOSE': 'true'}])
def test_app_init_env_verbose(app):
    assert app
    assert app.verbose is True


@pytest.mark.parametrize('env', [
    {'WORK_DIR_REMOVED': 'true'},
    {'WORK_DIR_REMOVED': 'false'},
])
def test_app_init_env_work_dir_removed(app, env):
    assert app
    value = True if env['WORK_DIR_REMOVED'] == 'true' else False
    assert app.is_work_dir_removed is value


def test_rpm_py_version_info_is_ok(app):
    app.rpm_py_version = '4.14.0-rc1'
    version_info = app.rpm_py_version_info
    assert version_info == ('4', '14', '0', 'rc1')


def test_verify_system_status_is_ok(app):
    app._is_rpm_package_installed = mock.MagicMock(return_value=True)
    app._verify_system_status()
    assert True


def test_verify_system_status_is_skipped_sys_python_and_rpm_py_installed(app):
    app._is_system_python = mock.MagicMock(return_value=True)
    app._is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.raises(InstallSkipError):
        app._verify_system_status()

    assert True


def test_verify_system_status_is_error_on_sys_py_and_rpm_py_not_installed(app):
    app._is_system_python = mock.MagicMock(return_value=True)
    app._is_python_binding_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app._verify_system_status()
    expected_message = '''
RPM Python binding on system Python should be installed manually.
Install the proper RPM package of python{,2,3}-rpm.
'''
    assert expected_message == str(ei.value)


def test_verify_system_status_is_error_on_sys_rpm_and_missing_packages(app):
    app._is_system_rpm = mock.MagicMock(return_value=True)
    app._is_rpm_package_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app._verify_system_status()
    expected_message = '''
Required RPM not installed: [rpm-libs, rpm-devel].
Install the RPM package.
'''
    assert expected_message == str(ei.value)


@pytest.mark.parametrize('package_name', ['rpm-lib'])
def test_is_rpm_package_installed_returns_true(app, package_name):
    assert not app._is_rpm_package_installed(package_name)


def test_is_rpm_package_installed_returns_false(app):
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        mock_sh_e.side_effect = InstallError('test.')
        assert not app._is_rpm_package_installed('dummy')


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
    tag_names = app._predict_candidate_git_tag_names()
    assert tag_names == value_dict['tag_names']


def test_download_and_expand_rpm_py_is_ok_from_archive_url(app):
    app.git_branch = None
    # app.rpm_py_version = '4.14.0-rc1'
    target_top_dir_name = 'foo'
    app._download_and_expand_from_archive_url = mock.MagicMock(
        return_value=target_top_dir_name)
    top_dir_name = app._download_and_expand_rpm_py()
    assert app._download_and_expand_from_archive_url.called
    assert top_dir_name == target_top_dir_name


def test_download_and_expand_rpm_py_is_ok_by_git(app):
    app.git_branch = 'foo'
    target_top_dir_name = 'bar'
    app._download_and_expand_by_git = mock.MagicMock(
        return_value=target_top_dir_name)
    top_dir_name = app._download_and_expand_rpm_py()
    assert app._download_and_expand_by_git.called
    assert top_dir_name == target_top_dir_name


def test_download_and_expand_rpm_py_is_failed_on_archive_url_ok_on_git(app):
    app.git_branch = None

    def mock_predict_candidate_git_tag_names(*args, **kwargs):
        return [
            'rpm-1.2.3-dummy',
            'rpm-4.5.6-dummy',
        ]

    app._predict_candidate_git_tag_names = mock_predict_candidate_git_tag_names
    app.rpm_py_version = '4.13.0'

    target_top_dir_name = 'bar'
    app._download_and_expand_by_git = mock.MagicMock(
        return_value=target_top_dir_name)

    with pytest.helpers.work_dir():
        top_dir_name = app._download_and_expand_rpm_py()
        app._download_and_expand_by_git.called
        assert top_dir_name == target_top_dir_name


def test_download_and_expand_by_git_is_ok(app):
    # Existed branch
    app.git_branch = 'rpm-4.14.x'
    with pytest.helpers.work_dir():
        top_dir_name = app._download_and_expand_by_git()
        assert top_dir_name == 'rpm'


def test_download_and_expand_by_git_is_failed(app):
    # Not existed branch
    app.git_branch = 'rpm-4.14.x-dummy'
    with pytest.helpers.work_dir():
        with pytest.raises(InstallError):
            app._download_and_expand_by_git()


def test_download_and_expand_by_git_is_ok_with_predicted_branch(app):
    app.git_branch = None
    app._predict_git_branch = mock.MagicMock(
        return_value='rpm-4.13.0.1')
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        top_dir_name = app._download_and_expand_by_git()
        mock_sh_e.called
        assert top_dir_name == 'rpm'


@pytest.mark.parametrize('value_dict', [
    {
        # Set version name with the major version and minior version
        # mapping to the stable branch.
        'version_info': ('4', '13', '0'),
        'branch': 'rpm-4.13.x',
    },
    {
        # Set version name not mapping to the stable branch.
        # to get the source from master branch.
        # It is likely to be used for development.
        'version_info': ('5', '99', '0', 'dev'),
        'branch': 'master',
    },
])
@mock.patch.object(Log, 'verbose', new=False)
def test_predict_git_branch(app, value_dict, monkeypatch):
    app.git_branch = None
    version_info = value_dict['version_info']
    monkeypatch.setattr(type(app), 'rpm_py_version_info',
                        mock.PropertyMock(return_value=version_info))
    branch = app._predict_git_branch()
    assert branch == value_dict['branch']


@mock.patch.object(Log, 'verbose', new=False)
def test_run_is_ok(app):
    app.is_work_dir_removed = True
    app._is_rpm_package_installed = mock.MagicMock(return_value=True)
    app.run()
    assert True


@pytest.mark.parametrize('rpm_py_version',
                         ['4.13.0', '4.14.0-rc1'])
@mock.patch.object(Log, 'verbose', new=False)
def test_run_is_ok_by_rpm_py_version(app, rpm_py_version):
    app.is_work_dir_removed = True
    app.rpm_py_version = rpm_py_version
    tag_names = app._predict_candidate_git_tag_names()
    top_dir_name = app._get_rpm_archive_top_dir_name(tag_names[0])

    def mock_download_and_expand_rpm_py(*args, **kwargs):
        rpm_py_dir = os.path.join(top_dir_name, 'python')
        os.makedirs(rpm_py_dir)
        return top_dir_name

    app._download_and_expand_rpm_py = mock_download_and_expand_rpm_py
    app._install_rpm_py = mock.MagicMock(return_value=True)
    app._is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.helpers.work_dir():
        app.run()
    assert True
