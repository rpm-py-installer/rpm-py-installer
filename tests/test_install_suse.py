"""
Tests for install.py for SUSE based Linux distributions

"""
import os
import shutil
from unittest import mock

import pytest

from install import Cmd, CmdError, RemoteFileNotFoundError

pytestmark = pytest.mark.skipif(
    not pytest.helpers.helper_is_suse(),
    reason="Tests for openSUSE/SUSE"
)


def test_rpm_download_raise_not_found_error(sys_rpm):
    with mock.patch.object(Cmd, 'sh_e') as mock_sh_e:
        ce = CmdError('test.')
        ce.stderr = 'Package \'dummy\' not found.\n'
        mock_sh_e.side_effect = ce
        with pytest.raises(RemoteFileNotFoundError) as exc:
            sys_rpm.download('dummy')
        assert mock_sh_e.called
        assert str(exc.value) == 'Package dummy not found on remote'


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


@pytest.mark.network
def test_app_verify_system_status_is_ok_on_sys_rpm_and_missing_pkgs(app):
    app.linux.rpm.is_system_rpm = mock.MagicMock(return_value=True)
    app.linux.verify_system_status()
