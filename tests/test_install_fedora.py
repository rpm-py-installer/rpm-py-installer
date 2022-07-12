"""
Tests for install.py for Fedora based Linux distributions

"""
import os
import shutil
import sys
from unittest import mock

import pytest

from install import (Cmd,
                     CmdError,
                     FedoraRpm,
                     InstallError,
                     Log,
                     RemoteFileNotFoundError,
                     RpmPyPackageNotFoundError)

pytestmark = pytest.mark.skipif(
    not pytest.helpers.helper_is_fedora_based(),
    reason="Tests for Fedora based Linux"
)


@pytest.mark.parametrize('is_dnf', [True, False])
def test_rpm_init_is_ok(is_dnf, sys_rpm_path, arch):
    with mock.patch.object(Cmd, 'which') as mock_which:
        mock_which.return_value = is_dnf
        rpm = FedoraRpm(sys_rpm_path)
        assert mock_which.called
        assert rpm.rpm_path == sys_rpm_path
        assert rpm.is_dnf is is_dnf
        assert rpm.arch == arch


@pytest.mark.parametrize('version_info,has_rpm_bulid_libs', [
    ((4, 8, 1),          False),
    ((4, 9, 0, 'beta1'), True),
    ((4, 9, 0, 'rc1'),   True),
    ((4, 9, 0),          True),
    ((4, 10, 0),         True),
])
def test_rpm_has_composed_rpm_bulid_libs_is_ok(
    local_rpm, version_info, has_rpm_bulid_libs, monkeypatch
):
    rpm = local_rpm
    monkeypatch.setattr(type(rpm), 'version_info',
                        mock.PropertyMock(return_value=version_info))
    assert rpm.has_composed_rpm_bulid_libs() == has_rpm_bulid_libs


@pytest.mark.parametrize('value_dict', [
    {
        'is_dnf': True,
        'cmd': 'dnf',
    },
    {
        'is_dnf': False,
        'cmd': 'yum',
    },
])
def test_rpm_package_cmd_is_ok(sys_rpm, value_dict):
    sys_rpm.is_dnf = value_dict['is_dnf']
    assert sys_rpm.package_cmd == value_dict['cmd']


@pytest.mark.parametrize('is_dnf', [True, False])
@pytest.mark.parametrize('installed', [True, False])
def test_rpm_is_downloadable_is_ok(sys_rpm, is_dnf, installed):
    sys_rpm.is_dnf = is_dnf
    sys_rpm.is_package_installed = mock.MagicMock(return_value=installed)
    assert sys_rpm.is_downloadable() is installed


@pytest.mark.parametrize('is_dnf', [True, False])
def test_rpm_download_is_ok(sys_rpm, is_dnf):
    sys_rpm.is_dnf = is_dnf
    with pytest.helpers.work_dir():
        with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
            sys_rpm.download('dummy')
            assert mock_sh_e.called


@pytest.mark.parametrize('is_dnf,stdout,stderr', [
    (True, '', 'foo\nNo package dummy.x86_64 available.\nbar\n'),
    (False, 'foo\nNo Match for argument dummy.x86_64\nbar\n', ''),
])
def test_rpm_download_raise_not_found_error(sys_rpm, is_dnf, stdout, stderr):
    sys_rpm.is_dnf = is_dnf
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        ce = CmdError('test.')
        ce.stdout = stdout
        ce.stderr = stderr
        mock_sh_e.side_effect = ce
        with pytest.raises(RemoteFileNotFoundError) as e:
            sys_rpm.download('dummy')
        assert mock_sh_e.called
        assert 'Package dummy not found on remote' == str(e.value)


def test_rpm_extract_is_ok(sys_rpm, rpm_files, monkeypatch):
    # mocking arch object for multi arch test cases.
    sys_rpm.arch = 'x86_64'
    with pytest.helpers.work_dir():
        for rpm_file in rpm_files:
            shutil.copy(rpm_file, '.')

        sys_rpm.extract('rpm-build-libs')
        files = os.listdir('./usr/lib64')
        files.sort()
        assert files == [
            'librpmbuild.so.7',
            'librpmbuild.so.7.0.1',
            'librpmsign.so.7',
            'librpmsign.so.7.0.1',
        ]


@pytest.mark.parametrize(
    'rpm_version_info,package_names_py3,package_names_py2',
    [
        (
            (4, 14, 0),
            ['python3-rpm'],
            ['python2-rpm'],
        ),
        (
            (4, 13, 0),
            ['python3-rpm', 'rpm-python3'],
            ['python2-rpm', 'rpm-python'],
        ),
        (
            (4, 12, 0),
            ['rpm-python3'],
            ['rpm-python'],
        ),
        (
            (4, 11, 1),
            ['rpm-python3'],
            ['rpm-python'],
        ),
        (
            (4, 11, 0),
            [],
            ['rpm-python'],
        ),
    ]
)
def test_installer_predict_rpm_py_package_names(
    installer, rpm_version_info, package_names_py3, package_names_py2,
    monkeypatch
):
    monkeypatch.setattr(type(installer.rpm), 'version_info',
                        mock.PropertyMock(return_value=rpm_version_info))
    expected_package_names = None
    if sys.version_info >= (3, 0):
        expected_package_names = package_names_py3
    else:
        expected_package_names = package_names_py2

    if expected_package_names:
        dst_package_names = installer._predict_rpm_py_package_names()
        assert dst_package_names == expected_package_names
    else:
        with pytest.raises(InstallError) as ie:
            installer._predict_rpm_py_package_names()
            assert 'No predicted pacakge' in str(ie.value)


@pytest.mark.parametrize('statuses', [
    [
        {'name': 'python3-rpm', 'side_effect': None},
    ],
    [
        {'name': 'rpm-python3', 'side_effect': None},
        {'name': 'rpm-python', 'side_effect': None},
    ],
    [
        {'name': 'rpm-python3', 'side_effect': RemoteFileNotFoundError},
        {'name': 'rpm-python', 'side_effect': None},
    ],
    [],
])
def test_installer_download_and_extract_rpm_py_package(installer, statuses):
    package_names = list(map(lambda status: status['name'], statuses))
    side_effects = list(map(lambda status: status['side_effect'], statuses))
    installer._predict_rpm_py_package_names = mock.Mock(
            return_value=package_names)
    installer.rpm.download_and_extract = mock.Mock(
        # Describe each side_effect called one by one.
        side_effect=side_effects
    )

    if statuses and side_effects[-1] is None:
        installer._download_and_extract_rpm_py_package()
        assert installer.rpm.download_and_extract.called
    else:
        with pytest.raises(RpmPyPackageNotFoundError):
            installer._download_and_extract_rpm_py_package()


def test_fedora_installer_install_from_rpm_py_package(installer, monkeypatch):
    dst_rpm_dir = 'dummy/dst/lib64/pythonX.Y/site-packages/rpm'
    rpm_dirs = [
        dst_rpm_dir,
        'dummy/dst/lib/pythonX.Y/site-packages/rpm'
    ]

    def download_and_extract_side_effect(*args):
        py_dir_name = 'python{0}.{1}'.format(
                      sys.version_info[0], sys.version_info[1])
        downloaded_rpm_dir = 'usr/lib64/{0}/site-packages/rpm'.format(
            py_dir_name
        )
        os.makedirs(downloaded_rpm_dir)
        pytest.helpers.touch(os.path.join(downloaded_rpm_dir, '__init__.py'))

    installer._download_and_extract_rpm_py_package = mock.Mock(
            side_effect=download_and_extract_side_effect)
    monkeypatch.setattr(type(installer.python), 'python_lib_rpm_dirs',
                        mock.PropertyMock(return_value=rpm_dirs))
    monkeypatch.setattr(type(installer.python), 'python_lib_rpm_dir',
                        mock.PropertyMock(return_value=dst_rpm_dir))

    with pytest.helpers.work_dir():
        assert not os.path.isfile(os.path.join(dst_rpm_dir, '__init__.py'))

        installer.install_from_rpm_py_package()

        assert os.path.isdir(dst_rpm_dir)
        assert os.path.isfile(os.path.join(dst_rpm_dir, '__init__.py'))


def test_installer_run_raises_error_for_rpm_build_libs(installer):
    installer.rpm.has_composed_rpm_bulid_libs = mock.MagicMock(
        return_value=True
    )
    installer._is_rpm_all_lib_include_files_installed = mock.MagicMock(
        return_value=False
    )
    installer.rpm.is_downloadable = mock.MagicMock(
        return_value=False
    )
    installer._is_rpm_build_libs_installed = mock.MagicMock(
        return_value=False
    )

    with pytest.raises(InstallError) as ei:
        installer.run()
    expected_message = '''
Install failed without rpm-devel package by below reason.
Can you install the RPM package, and run this installer again?

Required RPM not installed: [rpm-build-libs],
when a RPM download plugin not installed.
'''
    assert expected_message == str(ei.value)


@pytest.mark.network
def test_app_verify_system_status_is_error_on_sys_rpm_and_missing_pkgs(app):
    app.linux.rpm.is_system_rpm = mock.MagicMock(return_value=True)
    app.linux.rpm.is_package_installed = mock.MagicMock(return_value=False)
    with pytest.raises(InstallError) as ei:
        app.linux.verify_system_status()
    expected_message = '''
Required RPM not installed: [rpm-libs].
Install the RPM package.
'''
    assert expected_message == str(ei.value)


@pytest.mark.network
@pytest.mark.parametrize(
    'is_rpm_devel, is_popt_devel, is_downloadable, is_rpm_build_libs', [
        (True,  True, False, False),
        (False, False, True, True),
        (False, False, True, False),
    ], ids=[
        'rpm-devel and popt-devel installed',
        'rpm-devel, popt-devel not installed, RPM downloadable',
        'rpm-devel, popt-devel, rpm-build-libs not installed, '
        'RPM downloadable',
    ]
)
@mock.patch.object(Log, 'verbose', new=False)
def test_app_run_is_ok(
    app, is_rpm_devel, is_popt_devel, is_downloadable, is_rpm_build_libs,
    rpm_version_info_min_setup_py_in
):
    app.is_work_dir_removed = True
    app.rpm_py.installer._is_rpm_all_lib_include_files_installed = \
        mock.MagicMock(
            return_value=is_rpm_devel
        )
    app.rpm_py.installer._is_popt_devel_installed = mock.MagicMock(
        return_value=is_popt_devel
    )
    app.rpm_py.installer.rpm.is_downloadable = mock.MagicMock(
        return_value=is_downloadable
    )
    app.rpm_py.installer._is_rpm_build_libs_installed = mock.MagicMock(
        return_value=is_rpm_build_libs
    )
    if is_rpm_devel:
        app.rpm_py.installer._build_and_install = mock.MagicMock()
        app.python.is_python_binding_installed = mock.MagicMock(
            return_value=True
        )

    app.run()

    # If setup.py.in does not exist in old RPM, skip below checks.
    if app.linux.rpm.version_info < rpm_version_info_min_setup_py_in:
        return

    assert app.rpm_py.installer._is_rpm_all_lib_include_files_installed.called
    if not is_rpm_devel:
        assert app.rpm_py.installer.rpm.is_downloadable.called
        if is_downloadable:
            assert app.rpm_py.installer._is_rpm_build_libs_installed.called
