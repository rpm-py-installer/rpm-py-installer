"""
Tests for install.py

"""
import os
import re
import subprocess
import sys
import tempfile
from unittest import mock

import pytest
from install import (Cmd,
                     Downloader,
                     InstallError,
                     InstallSkipError,
                     Linux,
                     Log,
                     Python,
                     RemoteFileNotFoundError,
                     Rpm,
                     RpmPy,
                     RpmPyPackageNotFoundError,
                     RpmPyVersion,
                     SetupPy,
                     SuseRpm,
                     Utils)

from .conftest import get_rpm

RPM_ORG_VALID_ARCHIVE_URL_DICT = {
    'site': 'rpm.org',
    'url': 'http://ftp.rpm.org/releases'
           '/rpm-4.13.x/rpm-4.13.0.2.tar.bz2',
    'top_dir_name': 'rpm-4.13.0.2',
}

RPM_ORG_INVALID_ARCHIVE_URL_DICT = {
    'site': 'rpm.org',
    'url': 'http://ftp.rpm.org/releases'
           '/rpm-4.13.x/rpm-4.13.0.2-dummy.tar.bz2',
    'top_dir_name': 'rpm-4.13.0.2',
}
GIT_HUB_VALID_ARCHIVE_URL_DICT = {
    'site': 'github',
    'url': 'https://github.com/rpm-software-management/rpm/archive'
           '/rpm-4.13.0.2-release.tar.gz',
    'top_dir_name': 'rpm-rpm-4.13.0.2-release',
}
GIT_HUB_INVALID_ARCHIVE_URL_DICT = {
    'site': 'github',
    'url': 'https://github.com/rpm-software-management/rpm/archive'
           '/rpm-4.13.0.2-release-dummy.tar.gz',
    'top_dir_name': 'rpm-rpm-4.13.0.2-release',
}


@pytest.mark.parametrize('version_str,version_info', [
    (
        '4.13.0',
        (4, 13, 0),
    ),
    (
        '4.14.0-rc1',
        (4, 14, 0, 'rc1'),
    ),
])
def test_utils_version_str2tuple_is_ok(version_str, version_info):
    version_tuple = Utils.version_str2tuple(version_str)
    assert version_tuple == version_info


def test_cmd_sh_e_is_ok():
    stdout, stderr = Cmd.sh_e('pwd')
    assert not stdout
    assert stderr == ''


def test_cmd_sh_e_is_ok_with_stderr():
    stdout, stderr = Cmd.sh_e('echo "abc" 1>&2')
    assert not stdout
    assert stderr
    assert stderr == 'abc\n'


def test_cmd_sh_e_is_failed():
    with pytest.raises(InstallError):
        Cmd.sh_e('ls abcde')
    assert True


def test_cmd_sh_e_out_is_ok():
    stdout = Cmd.sh_e_out('pwd')
    assert stdout
    assert re.match(r'^.*\n$', stdout)


def test_cmd_cd_is_ok():
    with pytest.helpers.reset_dir():
        tmp_dir = tempfile.gettempdir()
        Cmd.cd(tmp_dir)
        cwd = os.getcwd()
        assert cwd == tmp_dir


def test_cmd_pushd_is_ok():
    with pytest.helpers.reset_dir():
        tmp_dir = tempfile.gettempdir()
        before_dir = os.getcwd()

        with Cmd.pushd(tmp_dir):
            a_dir = os.getcwd()
            assert a_dir == tmp_dir

        after_dir = os.getcwd()
        assert after_dir == before_dir

    pass


@pytest.mark.parametrize('cmd', ['rpm', 'git'])
def test_cmd_which_is_ok(cmd):
    abs_path = Cmd.which(cmd)
    assert re.match(r'^/.*{0}$'.format(cmd), abs_path)


@pytest.mark.network
def test_cmd_curl_is_ok(file_url):
    with pytest.helpers.work_dir():
        assert Cmd.curl_remote_name(file_url)


@pytest.mark.network
def test_cmd_curl_is_failed(file_url):
    not_existed_file_url = file_url + '.dummy'
    with pytest.helpers.work_dir():
        with pytest.raises(RemoteFileNotFoundError) as ei:
            Cmd.curl_remote_name(not_existed_file_url)
    assert re.match(r'^Download failed: .* HTTP Error 404: Not Found$',
                    str(ei.value))


@pytest.mark.parametrize('file_type', ['tar.gz', 'tar.bz2'])
def test_cmd_tar_archive_is_ok(archive_file_path_dicts, file_type):
    archive_file_path = archive_file_path_dicts[file_type]['valid']
    if not archive_file_path:
        raise ValueError('archive_file_path')
    with pytest.helpers.work_dir():
        Cmd.tar_extract(archive_file_path)
        assert os.path.isdir('a')


@pytest.mark.parametrize('file_type', ['tar.gz', 'tar.bz2'])
def test_cmd_tar_archive_is_failed(archive_file_path_dicts, file_type):
    archive_file_path = archive_file_path_dicts[file_type]['invalid']
    if not archive_file_path:
        raise ValueError('archive_file_path')

    with pytest.helpers.work_dir():
        with pytest.raises(InstallError) as ei:
            Cmd.tar_extract(archive_file_path)
    assert re.match(r'^Extract failed: .* could not be opened successfully$',
                    str(ei.value))


def test_cmd_find_is_ok():
    with pytest.helpers.work_dir():
        os.makedirs('dir1/dir2')
        pytest.helpers.touch('dir1/dir2/a.txt')
        pytest.helpers.touch('dir1/b.txt')
        pytest.helpers.touch('dir1/a.rpm')
        pytest.helpers.run_cmd('ln -s dir1/b.txt dir1/c.txt')
        matched_files = Cmd.find('.', '*.txt')
        assert matched_files == [
            './dir1/b.txt',
            './dir1/dir2/a.txt',
        ]
        matched_files = Cmd.find('.', 'a.txt')
        assert matched_files == [
            './dir1/dir2/a.txt',
        ]
        matched_files = Cmd.find('.', 'a.*')
        assert matched_files == [
            './dir1/a.rpm',
            './dir1/dir2/a.txt',
        ]


def test_cmd_mkdir_p_is_ok():
    with pytest.helpers.work_dir():
        Cmd.mkdir_p('./a/b')
        pytest.helpers.touch('./a/b/c.txt')
    assert True


def test_python_init():
    python_path = '/usr/bin/python'
    python = Python(python_path)
    assert python.python_path
    assert python.python_path == python_path


@pytest.mark.parametrize('python_path', [
    '/usr/bin/python', '/usr/bin/python3.6'
])
def test_python_is_system_python_returns_true(python_path):
    python = Python(python_path)
    assert python.is_system_python()


def test_python_is_system_python_returns_false():
    python_path = '/usr/local/bin/python'
    python = Python(python_path)
    assert python.is_system_python() is False


@pytest.mark.parametrize('rpm_py_name',
                         ['rpm', 'rpm-python'])
def test_python_is_python_binding_installed_on_pip_9(rpm_py_name):
    value_dicts = [
        {
            'json_rpm_py_obj': {
                'name': rpm_py_name,
                'version': '1.2.3',
            },
            'installed': True
        },
        {
            'json_rpm_py_obj': {
                'name': 'dummy',
                'version': '1.2.3',
            },
            'installed': False
        },
    ]
    python = Python('/usr/bin/python')
    python._get_pip_version = mock.MagicMock(return_value='9.0.0')

    for value_dict in value_dicts:
        json_rpm_py_obj = value_dict['json_rpm_py_obj']
        installed = value_dict['installed']

        json_obj = [json_rpm_py_obj]
        python._get_pip_list_json_obj = mock.MagicMock(return_value=json_obj)
        assert python.is_python_binding_installed_on_pip() is installed


@pytest.mark.parametrize('rpm_py_name',
                         ['rpm', 'rpm-python'])
def test_python_is_python_binding_installed_on_pip_less_than_9(rpm_py_name):
    value_dicts = [
        {
            'lines': [
                '{0} (1.2.3)'.format(rpm_py_name),
            ],
            'installed': True,
        },
        {
            'lines': [
                'dummy (1.2.3)',
                'rpm-py-installer (1.2.3)',
            ],
            'installed': False,
        },
    ]
    python = Python('/usr/bin/python')
    python._get_pip_version = mock.MagicMock(return_value='8.9.9')

    for value_dict in value_dicts:
        lines = value_dict['lines']
        installed = value_dict['installed']

        python._get_pip_list_lines = mock.MagicMock(return_value=lines)
        assert python.is_python_binding_installed_on_pip() is installed


def test_rpm_init_raises_error_on_not_existed_rpm(is_debian, is_suse):
    with pytest.raises(InstallError) as ei:
        get_rpm(is_debian, is_suse, '/usr/bin/rpm123')
    expected_message = "RPM binary command '/usr/bin/rpm123' not found."
    assert expected_message == str(ei.value)


def test_rpm_version_is_ok(sys_rpm):
    assert sys_rpm.version
    assert re.match(r'^\d\.\d', sys_rpm.version)


def test_rpm_version_info_is_ok(monkeypatch, local_rpm):
    rpm = local_rpm
    monkeypatch.setattr(type(rpm), 'version',
                        mock.PropertyMock(return_value='4.14.0.rc1'))
    info = rpm.version_info
    assert info
    assert isinstance(info, tuple)
    assert info == (4, 14, 0, 'rc1')


def test_rpm_is_system_rpm_returns_true(sys_rpm):
    assert sys_rpm.is_system_rpm()


def test_rpm_is_system_rpm_returns_false(local_rpm):
    rpm = local_rpm
    assert rpm.is_system_rpm() is False


@pytest.mark.parametrize('package_name', ['rpm-lib'])
def test_rpm_is_package_installed_returns_true(sys_rpm, package_name):
    assert not sys_rpm.is_package_installed(package_name)


def test_rpm_is_package_installed_returns_false(sys_rpm):
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        mock_sh_e.side_effect = InstallError('test.')
        assert not sys_rpm.is_package_installed('dummy')


def test_rpm_lib_dir_is_ok(sys_rpm, is_debian, arch):
    if is_debian:
        lib_dir = '/usr/lib/{0}-linux-gnu'.format(arch)
        assert sys_rpm.lib_dir == lib_dir
    else:
        # 64-bit: /usr/lib64, 32-bit: /usr/lib
        assert re.match(r'^/usr/lib(64)?$', sys_rpm.lib_dir)


@pytest.mark.parametrize('version,info,is_release,git_branch', [
    (
        '4.13.0',
        (4, 13, 0),
        True,
        'rpm-4.13.x',
    ),
    (
        '4.14.0-rc1',
        (4, 14, 0, 'rc1'),
        False,
        'rpm-4.14.x',
    ),
])
def test_rpm_py_version_is_ok(version, info, is_release, git_branch):
    rpm_py_version = RpmPyVersion(version)
    assert '{0}'.format(rpm_py_version) == version
    assert rpm_py_version.version == version
    assert rpm_py_version.info == info
    assert rpm_py_version.is_release is is_release
    assert rpm_py_version.git_branch == git_branch


@pytest.mark.parametrize(
    'file_name,os_id,id_like',
    [
        ('fedora-30', 'fedora', None),
        ('centos-7', 'centos', 'rhel fedora'),
        ('ubuntu-bionic', 'ubuntu', 'debian'),
    ]
)
def test_linux_os_release_items_are_ok_with_mock(
    os_release_dir, file_name, os_id, id_like
):
    os_release_file = os.path.join(os_release_dir, file_name)
    with mock.patch.object(Linux, 'OS_RELEASE_FILE', new=os_release_file):
        item_dict = Linux.os_release_items()
        assert item_dict['ID'] == os_id
        if id_like is not None:
            assert item_dict['ID_LIKE'] == id_like
        else:
            assert 'ID_LIKE' not in item_dict


def test_linux_os_release_items_are_ok():
    item_dict = Linux.os_release_items()
    # CentOS6 does not have /etc/os-release file.
    if 'ID' in item_dict:
        assert item_dict['ID']
        if item_dict['ID'] == 'fedora':
            assert 'ID_LIKE' not in item_dict
        elif item_dict['ID'] == 'centos':
            assert 'ID_LIKE' in item_dict
            assert item_dict['ID_LIKE'] == 'rhel fedora'
        elif item_dict['ID'] == 'ubuntu':
            assert 'ID_LIKE' in item_dict
            assert item_dict['ID_LIKE'] == 'debian'
        else:
            assert False, 'Unsupported ID {} for tests'.format(item_dict['ID'])


@pytest.mark.parametrize(
    'file_name,is_fedora',
    [
        ('fedora-30', True),
        ('centos-7', True),
        ('ubuntu-bionic', False),
        ('opensuse-tumbleweed', False),
    ]
)
def test_linux_is_fedora_ok_with_mock(os_release_dir, file_name, is_fedora):
    os_release_file = os.path.join(os_release_dir, file_name)
    with mock.patch.object(Linux, 'OS_RELEASE_FILE', new=os_release_file):
        with mock.patch.object(
                Linux, 'REDHAT_RELEASE_FILE', new="/this/file/does/not/exist"):
            assert Linux.is_fedora() is is_fedora


def test_linux_is_fedora_ok():
    item_dict = Linux.os_release_items()
    if 'ID' in item_dict:
        if item_dict['ID'] in ['fedora', 'centos']:
            assert Linux.is_fedora() is True
        elif item_dict['ID'] in ['ubuntu']:
            assert Linux.is_fedora() is False
        else:
            assert False, 'Unsupported ID {} for tests'.format(item_dict['ID'])
    else:
        if os.path.isfile(Linux.REDHAT_RELEASE_FILE):
            assert Linux.is_fedora() is True
        else:
            assert Linux.is_fedora() is False


@pytest.mark.parametrize(
    'file_name,class_name',
    [
        ('centos-7', 'FedoraLinux'),
        ('ubuntu-bionic', 'DebianLinux'),
        ('opensuse-tumbleweed', 'SuseLinux')
    ]
)
def test_linux_get_instance_is_ok_with_mock(
    os_release_dir, file_name, class_name, sys_rpm_path
):
    os_release_file = os.path.join(os_release_dir, file_name)
    python = Python()
    with mock.patch.object(Cmd, 'sh_e_out') as mock_sh_e_out:
        mock_sh_e_out.return_value = "x86_64"
        with mock.patch.object(Cmd, 'which') as mock_which:
            mock_which.return_value = None
            with mock.patch.object(Linux, 'OS_RELEASE_FILE',
                                   new=os_release_file):
                with mock.patch.object(
                        Linux, 'REDHAT_RELEASE_FILE',
                        new="/this/file/does/not/exist"):
                    linux = Linux.get_instance(python=python,
                                               rpm_path=sys_rpm_path)
                    assert linux.__class__.__name__ == class_name


@pytest.mark.parametrize('version,tag_names', [
    (
        '4.13.0',
        ['rpm-4.13.0-release', 'rpm-4.13.0'],
    ),
    (
        '4.14.0-rc1',
        ['rpm-4.14.0-rc1', 'rpm-4.14.0-rc1-release'],
    ),
])
def test_downloader_predict_candidate_git_tag_names_is_ok(version, tag_names):
    rpm_py_version = RpmPyVersion(version)
    downloader = Downloader(rpm_py_version)
    candidate_tag_names = downloader._predict_candidate_git_tag_names()
    assert candidate_tag_names == tag_names


def test_downloader_download_and_expand_is_ok_on_archive(downloader):
    downloader.git_branch = None
    target_top_dir_name = 'foo'
    downloader._download_and_expand_from_archive_url = mock.MagicMock(
        return_value=target_top_dir_name)
    top_dir_name = downloader.download_and_expand()
    assert downloader._download_and_expand_from_archive_url.called
    assert top_dir_name == target_top_dir_name


def test_downloader_download_and_expand_is_ok_on_git(downloader):
    downloader.git_branch = 'foo'
    target_top_dir_name = 'bar'
    downloader._download_and_expand_by_git = mock.MagicMock(
        return_value=target_top_dir_name)
    top_dir_name = downloader.download_and_expand()
    assert downloader._download_and_expand_by_git.called
    assert top_dir_name == target_top_dir_name


def test_downloader_download_and_expand_is_ng_on_archive_ok_on_git(downloader):
    downloader.git_branch = None
    downloader._download_and_expand_from_archive_url = mock.Mock(
        side_effect=RemoteFileNotFoundError('test.')
    )
    target_top_dir_name = 'bar'
    downloader._download_and_expand_by_git = mock.Mock(
               return_value=target_top_dir_name)

    with pytest.helpers.work_dir():
        top_dir_name = downloader.download_and_expand()
        downloader._download_and_expand_by_git.called
        assert top_dir_name == target_top_dir_name


@pytest.mark.network
@pytest.mark.parametrize('archive_dicts,is_ok', [
    (
        [RPM_ORG_VALID_ARCHIVE_URL_DICT],
        True,
    ),
    (
        [GIT_HUB_VALID_ARCHIVE_URL_DICT],
        True,
    ),
    (
        [RPM_ORG_INVALID_ARCHIVE_URL_DICT, GIT_HUB_VALID_ARCHIVE_URL_DICT],
        True,
    ),
    (
        [RPM_ORG_INVALID_ARCHIVE_URL_DICT, GIT_HUB_INVALID_ARCHIVE_URL_DICT],
        False,
    )
], ids=[
    'rpm.org valid URL',
    'github valid URL',
    'rpm.org invalid URL => github valid URL',
    'rpm.org invalid URL => github invalid URL',
])
def test_downloader_download_and_expand_from_archive_url(
    downloader, archive_dicts, is_ok
):
    downloader._get_candidate_archive_dicts = mock.Mock(
        return_value=archive_dicts
    )
    with pytest.helpers.work_dir():
        if is_ok:
            top_dir_name = downloader._download_and_expand_from_archive_url()
            assert top_dir_name
            assert os.path.isdir(top_dir_name)
        else:
            with pytest.raises(RemoteFileNotFoundError):
                downloader._download_and_expand_from_archive_url()


@pytest.mark.parametrize('version,archive_dicts', [
    (
        '4.13.0',
        [
            {
                'site': 'github',
                'url': 'https://github.com/rpm-software-management/rpm'
                       '/archive/rpm-4.13.0-release.tar.gz',
                'top_dir_name': 'rpm-rpm-4.13.0-release',
            },
            {
                'site': 'github',
                'url': 'https://github.com/rpm-software-management/rpm'
                       '/archive/rpm-4.13.0.tar.gz',
                'top_dir_name': 'rpm-rpm-4.13.0',
            },
            {
                'site': 'rpm.org',
                'url': 'http://ftp.rpm.org/releases/'
                       'rpm-4.13.x/rpm-4.13.0.tar.gz',
                'top_dir_name': 'rpm-4.13.0',
            },
        ],
    ),
    (
        '4.14.0-rc1',
        [
            {
                'site': 'github',
                'url': 'https://github.com/rpm-software-management/rpm'
                       '/archive/rpm-4.14.0-rc1.tar.gz',
                'top_dir_name': 'rpm-rpm-4.14.0-rc1',
            },
            {
                'site': 'github',
                'url': 'https://github.com/rpm-software-management/rpm'
                       '/archive/rpm-4.14.0-rc1-release.tar.gz',
                'top_dir_name': 'rpm-rpm-4.14.0-rc1-release',
            },
        ],
    ),
])
def test_downloader_get_candidate_archive_dicts_is_ok(version, archive_dicts):
    rpm_py_version = RpmPyVersion(version)
    downloader = Downloader(rpm_py_version)
    candidate_archive_dicts = downloader._get_candidate_archive_dicts()
    assert candidate_archive_dicts == archive_dicts


@pytest.mark.network
def test_downloader_download_and_expand_by_git_is_ok(downloader):
    # Existed branch
    downloader.git_branch = 'rpm-4.14.x'
    with pytest.helpers.work_dir():
        top_dir_name = downloader._download_and_expand_by_git()
        assert top_dir_name == 'rpm'


@pytest.mark.network
def test_downloader_download_and_expand_by_git_is_failed(downloader):
    # Not existed branch
    downloader.git_branch = 'rpm-4.14.x-dummy'
    with pytest.helpers.work_dir():
        with pytest.raises(InstallError) as ei:
            downloader._download_and_expand_by_git()
        expected_message = (
            'fatal: Remote branch rpm-4.14.x-dummy not '
            'found in upstream origin'
        )
        assert expected_message in str(ei.value)


def test_downloader_download_and_expand_by_git_is_ok_with_predicted(
    downloader
):
    downloader.git_branch = None
    downloader._predict_git_branch = mock.MagicMock(
        return_value='rpm-4.13.0.1')
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        mock_sh_e.return_value = ('stdout', 'stderr')
        top_dir_name = downloader._download_and_expand_by_git()
        assert mock_sh_e.called
        assert top_dir_name == 'rpm'


@pytest.mark.network
@pytest.mark.parametrize('value_dict', [
    {
        # Set version name with the major version and minior version
        # mapping to the stable branch.
        'version_info': (4, 13, 0),
        'branch': 'rpm-4.13.x',
    },
    {
        # Set version name not mapping to the stable branch.
        # to get the source from master branch.
        # It is likely to be used for development.
        'version_info': (5, 99, 0, 'dev'),
        'branch': 'master',
    },
])
@mock.patch.object(Log, 'verbose', new=False)
def test_downloader_predict_git_branch(downloader, value_dict, monkeypatch):
    version_info = value_dict['version_info']
    monkeypatch.setattr(type(downloader.rpm_py_version), 'info',
                        mock.PropertyMock(return_value=version_info))
    branch = downloader._predict_git_branch()
    assert branch == value_dict['branch']


def test_setup_py_init_is_ok(setup_py):
    assert setup_py
    assert setup_py.version
    assert setup_py.replaced_word_dict
    assert isinstance(setup_py.replaced_word_dict, dict)
    assert isinstance(setup_py.patches, list)
    assert len(setup_py.patches) == 2


def test_setup_py_add_patchs_to_build_without_pkg_config(setup_py):
    setup_py.add_patchs_to_build_without_pkg_config('/usr/lib64',
                                                    '/usr/include')
    assert len(setup_py.patches) == 5


@pytest.mark.parametrize('use_add_patchs', [False, True])
def test_setup_py_apply_and_save(use_add_patchs):
    rpm_py_version = RpmPyVersion('4.14.0-rc1')
    setup_py = SetupPy(rpm_py_version)
    assert len(setup_py.patches) == 2

    with pytest.helpers.work_dir_with_setup_py():
        if use_add_patchs:
            setup_py.add_patchs_to_build_without_pkg_config(
                '/usr/lib64', '/usr/include'
            )
            assert len(setup_py.patches) == 5
        setup_py.apply_and_save()
        with open(setup_py.OUT_PATH) as f_out:
            content = f_out.read()
            assert '@PACKAGE_NAME@' not in content
            assert '@VERSION@' not in content
            assert '@PACKAGE_BUGREPORT@' not in content

        print(setup_py.patches)
        for patch in setup_py.patches:
            if patch.get('required'):
                assert patch.get('applied')


def test_installer_init_is_ok(installer):
    assert installer
    assert installer.rpm_py_version
    assert installer.python
    assert installer.rpm
    assert installer.setup_py
    assert installer.optimized is True
    assert installer.setup_py_opts == '-q'


@pytest.mark.network
@pytest.mark.skipif(pytest.helpers.helper_is_suse() and
                    not pytest.helpers.is_root_user(),
                    reason="Can only run zypper as root.")
def test_installer_install_from_rpm_py_package(
    installer, is_debian, is_centos, monkeypatch
):
    with pytest.helpers.work_dir():
        # The RPM Python binding for python3 is not provided on CentOS.
        # rpm-python3 does not exist on CentOS.
        # http://mirror.centos.org/centos/7/os/x86_64/Packages/
        if is_debian or \
           not installer._predict_rpm_py_package_names() or \
           (is_centos and sys.version_info >= (3, 0)):
            with pytest.raises(RpmPyPackageNotFoundError):
                installer.install_from_rpm_py_package()
        else:
            dst_rpm_dir = 'dummy/dst/site-packages/rpm'
            monkeypatch.setattr(type(installer.python), 'python_lib_rpm_dir',
                                mock.PropertyMock(return_value=dst_rpm_dir))
            assert not os.path.isfile(os.path.join(dst_rpm_dir, '__init__.py'))

            try:
                installer.install_from_rpm_py_package()

                assert os.path.isdir(dst_rpm_dir)
                assert os.path.isfile(os.path.join(dst_rpm_dir, '__init__.py'))
            except RpmPyPackageNotFoundError:
                message = (
                    "Cann't test the different Python version's binary case."
                )
                pytest.skip(message)


def test_installer_make_dep_lib_file_links_and_copy_include_files(installer):
    installer._rpm_py_has_popt_devel_dep = mock.MagicMock(
        return_value=True
    )
    installer._is_popt_devel_installed = mock.MagicMock(
        return_value=False
    )
    installer._is_package_downloadable = mock.MagicMock(
        return_value=False
    )
    with pytest.raises(InstallError) as ei:
        installer._make_dep_lib_file_sym_links_and_copy_include_files()
    expected_message = '''
Install a {0} download plugin or
install the {0} package [{1}].
'''.format(installer.package_sys_name, installer.package_popt_devel_name)
    assert expected_message == str(ei.value)


@pytest.mark.parametrize(
    'is_installed_from_bin,install_from_bin_ok,setup_py_in_exists',
    [
        (True,  True,  True),
        (True,  False, True),
        (False, True,  True),
        (True,  True,  False),
        (False, True,  False),
    ]
)
def test_rpm_py_download_and_install(
    is_installed_from_bin, install_from_bin_ok, setup_py_in_exists, rpm_py
):
    rpm_py.is_installed_from_bin = is_installed_from_bin
    top_dir_name = 'rpm-{0}'.format(rpm_py.version.version)
    rpm_py.downloader.download_and_expand = mock.Mock(
        return_value=top_dir_name)
    rpm_py.installer.run = mock.Mock(
        return_value=None)
    if install_from_bin_ok:
        rpm_py.installer.install_from_rpm_py_package = mock.Mock(
            return_value=None)
    else:
        rpm_py.installer.install_from_rpm_py_package = mock.Mock(
            side_effect=RpmPyPackageNotFoundError('test.'))

    with pytest.helpers.work_dir():
        python_dir = os.path.join(top_dir_name, 'python')
        os.makedirs(python_dir)
        if setup_py_in_exists:
            pytest.helpers.touch(os.path.join(python_dir, 'setup.py.in'))

        rpm_py.download_and_install()

        if is_installed_from_bin:
            assert rpm_py.installer.install_from_rpm_py_package.called
            if install_from_bin_ok:
                assert not rpm_py.installer.run.called
            else:
                assert rpm_py.installer.run.called
        else:
            if setup_py_in_exists:
                assert rpm_py.installer.run.called
                assert not rpm_py.installer.install_from_rpm_py_package.called
            else:
                assert not rpm_py.installer.run.called
                assert rpm_py.installer.install_from_rpm_py_package.called


def test_app_init(app):
    assert app
    assert app.verbose is False
    assert app.python
    assert isinstance(app.python, Python)
    assert app.linux
    assert isinstance(app.linux, Linux)
    assert app.linux.rpm
    assert app.linux.sys_installed is False
    assert isinstance(app.linux.rpm, Rpm)
    assert app.rpm_py
    assert isinstance(app.rpm_py, RpmPy)
    # Actual string is N.N.N.N or N.N.N.N-(rc|beta)N
    # Check verstion string roughly right now.
    assert re.match(r'^[\d.]+(-[a-z\d]+)?$', app.rpm_py.version.version)
    assert app.rpm_py.downloader.git_branch is None
    assert app.rpm_py.installer.optimized is True
    assert app.rpm_py.installer.setup_py_opts == '-q'
    assert app.is_work_dir_removed is True


@pytest.mark.parametrize('env', [{'RPM_PY_RPM_BIN': 'rpm'}])
def test_app_init_env_rpm(app):
    assert app
    assert re.match(r'^/.+/rpm$', app.linux.rpm.rpm_path)


@pytest.mark.parametrize('env', [{'RPM_PY_VERSION': '1.2.3'}])
def test_app_init_env_rpm_py_version(app):
    assert app
    assert app.rpm_py.version.version == '1.2.3'


@pytest.mark.parametrize('env', [{'RPM_PY_GIT_BRANCH': 'master'}])
def test_app_init_env_git_branch(app):
    assert app
    assert app.rpm_py.downloader.git_branch == 'master'


@pytest.mark.parametrize('env', [
    {'RPM_PY_OPTM': 'true'},
    {'RPM_PY_OPTM': 'false'},
])
def test_app_init_env_setup_py_optm(app, env):
    assert app
    value = True if env['RPM_PY_OPTM'] == 'true' else False
    assert app.rpm_py.installer.optimized is value


@pytest.mark.parametrize('env', [{'RPM_PY_VERBOSE': 'true'}])
def test_app_init_env_verbose(app):
    assert app
    assert app.verbose is True


@pytest.mark.parametrize('env', [
    {'RPM_PY_WORK_DIR_REMOVED': 'true'},
    {'RPM_PY_WORK_DIR_REMOVED': 'false'},
])
def test_app_init_env_work_dir_removed(app, env):
    assert app
    value = True if env['RPM_PY_WORK_DIR_REMOVED'] == 'true' else False
    assert app.is_work_dir_removed is value


@pytest.mark.network
def test_app_verify_system_status_is_ok(app):
    app.linux.rpm.is_package_installed = mock.MagicMock(return_value=True)
    app.linux.verify_system_status()
    assert True


def test_app_verify_system_status_skipped_on_sys_py_and_installed_rpm_py(app):
    app.python.is_system_python = mock.MagicMock(return_value=True)
    app.python.is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.raises(InstallSkipError):
        app.linux.verify_system_status()


def test_app_verify_system_status_is_ok_on_sys_py_and_sys_installed_true(app):
    app.python.is_system_python = mock.MagicMock(return_value=True)
    app.python.is_python_binding_installed = mock.MagicMock(return_value=False)
    app.linux.sys_installed = mock.MagicMock(return_value=True)
    app.linux.verify_system_status()
    assert True


def test_app_verify_system_status_is_error_on_sys_py_and_no_rpm_py(app):
    app.python.is_system_python = mock.MagicMock(return_value=True)
    app.python.is_python_binding_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app.linux.verify_system_status()
    expected_message = '''
RPM Python binding on system Python should be installed manually.
Install the proper RPM package of python{,2,3}-rpm,
or set a environment variable RPM_PY_SYS=true
'''
    assert expected_message == str(ei.value)


@mock.patch('install.Cmd.sh_e')
@mock.patch('os.walk')
@mock.patch('os.rename')
def test_suse_rpm_download_tumbleweed(
        mock_os_rename, mock_os_walk, mock_sh_e, sys_rpm_path):
    mock_os_walk.return_value = (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.14.2.1-6.1.x86_64.rpm',
          'python3-3.7.3-1.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-6.1.x86_64.rpm']),
        ("/var/cache/zypp/packages/repo-oss/noarch", [],
         ['python3-tox-3.12.1-1.4.noarch.rpm'])
    )
    suse_rpm = SuseRpm(sys_rpm_path)
    suse_rpm.download("rpm")

    assert mock_sh_e.call_args_list[-1] == \
        mock.call(
            "zypper --non-interactive -v install -f --download-only rpm",
            stderr=subprocess.PIPE)
    assert mock_os_rename.call_args_list[0] == \
        mock.call(
            "/var/cache/zypp/packages/repo-oss/x86_64/"
            "rpm-4.14.2.1-6.1.x86_64.rpm",
            "./rpm-4.14.2.1-6.1.x86_64.rpm")


@mock.patch('install.Cmd.sh_e')
@mock.patch('os.walk')
@mock.patch('os.rename')
def test_suse_rpm_download_leap(
        mock_os_rename, mock_os_walk, mock_sh_e, sys_rpm_path):
    mock_os_walk.return_value = (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.14.1-lp151.13.10.x86_64.rpm',
          'python3-3.6.3-lp151.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-lp151.1.x86_64.rpm']),
        ("/var/cache/zypp/packages/repo-oss/noarch", [],
         ['python3-tox-3.12.1-1.4.noarch.rpm'])
    )
    suse_rpm = SuseRpm(sys_rpm_path)
    suse_rpm.download("rpm")

    assert mock_sh_e.call_args_list[-1] == \
        mock.call(
            "zypper --non-interactive -v install -f --download-only rpm",
            stderr=subprocess.PIPE)
    assert mock_os_rename.call_args_list[0] == \
        mock.call(
            "/var/cache/zypp/packages/repo-oss/x86_64/"
            "rpm-4.14.1-lp151.13.10.x86_64.rpm",
            "./rpm-4.14.1-lp151.13.10.x86_64.rpm")


@mock.patch('install.Cmd.sh_e')
@mock.patch('os.walk')
@mock.patch('os.rename')
def test_suse_rpm_download_rpm_missing(
        mock_os_rename, mock_os_walk, mock_sh_e, sys_rpm_path):
    mock_os_walk.return_value = ()
    suse_rpm = SuseRpm(sys_rpm_path)
    with pytest.raises(InstallError) as inst_err:
        suse_rpm.download("rpm")

    assert mock_sh_e.call_args_list[-1] == \
        mock.call(
            "zypper --non-interactive -v install -f --download-only rpm",
            stderr=subprocess.PIPE)
    assert not mock_os_rename.called
    assert "Could not find downloaded package rpm in " \
        "/var/cache/zypp/packages" in str(inst_err)


@pytest.mark.parametrize('os_walk_retval', [
    (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.12.2.1-6.1.x86_64.rpm', 'rpm-4.13.1.1-6.1.x86_64.rpm',
          'rpm-4.14.2.1-6.1.x86_64.rpm', 'python3-3.7.3-1.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-6.1.x86_64.rpm'])),
    (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.14.2.1-5.1.x86_64.rpm', 'rpm-4.14.2.1-6.0.x86_64.rpm',
          'rpm-4.14.2.1-6.1.x86_64.rpm', 'python3-3.7.3-1.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-6.1.x86_64.rpm'])
    )
])
@mock.patch('install.Cmd.sh_e')
@mock.patch('os.walk')
@mock.patch('os.rename')
def test_suse_rpm_download_multiple_cached_files_tumbleweed(
        mock_os_rename, mock_os_walk, mock_sh_e, os_walk_retval, sys_rpm_path):
    mock_os_walk.return_value = os_walk_retval
    suse_rpm = SuseRpm(sys_rpm_path)
    suse_rpm.download("rpm")

    assert mock_sh_e.call_args_list[-1] == \
        mock.call(
            "zypper --non-interactive -v install -f --download-only rpm",
            stderr=subprocess.PIPE)
    assert mock_os_rename.call_args_list[0] == \
        mock.call(
            "/var/cache/zypp/packages/repo-oss/"
            "x86_64/rpm-4.14.2.1-6.1.x86_64.rpm",
            "./rpm-4.14.2.1-6.1.x86_64.rpm")


@pytest.mark.parametrize('os_walk_retval', [
    (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.12.2.1-lp151.1.x86_64.rpm', 'rpm-4.13.1.1-lp151.1.x86_64.rpm',
          'rpm-4.14.2.1-lp151.1.x86_64.rpm',
          'python3-3.7.3-lp151.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-lp151.1.x86_64.rpm'])),
    (
        ("/var/cache/zypp/packages/", ['repo-oss'], []),
        ("/var/cache/zypp/packages/repo-oss", ['x86_64', 'noarch'], []),
        ("/var/cache/zypp/packages/repo-oss/x86_64", [],
         ['rpm-4.14.2.1-lp151.0.1.x86_64.rpm',
          'rpm-4.14.2.1-lp151.0.x86_64.rpm', 'rpm-4.14.2.1-lp151.1.x86_64.rpm',
          'python3-3.7.3-lp151.2.x86_64.rpm',
          'python3-rpm-4.14.2.1-lp151.1.x86_64.rpm'])
    )
])
@mock.patch('install.Cmd.sh_e')
@mock.patch('os.walk')
@mock.patch('os.rename')
def test_suse_rpm_download_multiple_cached_files_leap(
        mock_os_rename, mock_os_walk, mock_sh_e, os_walk_retval, sys_rpm_path):
    mock_os_walk.return_value = os_walk_retval
    suse_rpm = SuseRpm(sys_rpm_path)
    suse_rpm.download("rpm")

    assert mock_sh_e.call_args_list[-1] == \
        mock.call(
            "zypper --non-interactive -v install -f --download-only rpm",
            stderr=subprocess.PIPE)
    assert mock_os_rename.call_args_list[0] == \
        mock.call(
            "/var/cache/zypp/packages/repo-oss/"
            "x86_64/rpm-4.14.2.1-lp151.1.x86_64.rpm",
            "./rpm-4.14.2.1-lp151.1.x86_64.rpm")


@pytest.mark.network
@pytest.mark.parametrize('rpm_py_version',
                         ['4.13.0', '4.14.0-rc1'])
@mock.patch.object(Log, 'verbose', new=False)
def test_app_run_is_ok_on_download_by_rpm_py_version(app, rpm_py_version):
    app.is_work_dir_removed = True

    app.rpm_py.downloader.rpm_py_version = RpmPyVersion(rpm_py_version)

    tag_names = app.rpm_py.downloader._predict_candidate_git_tag_names()
    top_dir_name = app.rpm_py.downloader._get_git_hub_archive_top_dir_name(
                   tag_names[0])

    def mock_download_and_expand(*args, **kwargs):
        rpm_py_dir = os.path.join(top_dir_name, 'python')
        os.makedirs(rpm_py_dir)
        return top_dir_name

    app.rpm_py.downloader.download_and_expand = mock_download_and_expand
    app.rpm_py.installer.setup_py.exists_in_path = mock.MagicMock(
        return_value=True
    )
    app.rpm_py.installer.run = mock.MagicMock(return_value=True)
    app.python.is_python_binding_installed = mock.MagicMock(return_value=True)

    with pytest.helpers.work_dir():
        app.run()
    assert True
