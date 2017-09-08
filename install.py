#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager


class Application(object):
    RPM_ARCHIVE_URL_FORMAT = (
        'https://github.com/rpm-software-management/rpm/archive'
        '/rpm-{version}-release.tar.gz'
    )
    RPM_ARCHIVE_TOP_DIR_FORMAT = 'rpm-rpm-{version}-release'

    def __init__(self):
        self.load_options_from_env()

    def run(self):
        try:
            self.verify_system_status()
        except InstallSkipError as ise:
            Log.info('Install skipped.')
            return

        work_dir = tempfile.mkdtemp(suffix='-rpm-py-installer')
        Log.info("Created working directory '{0}'".format(work_dir))

        with Cmd.pushd(work_dir):
            self.download_and_expand_rpm_py()

            rpm_py_dir = os.path.join(self.rpm_archive_top_dir, 'python')
            Cmd.cd(rpm_py_dir)

            self.install_rpm_py()
            if not self.is_python_binding_installed():
                message = (
                    'RPM Python binding module failed to install '
                    'with unknown reason.'
                )
                raise InstallError(message)

            # TODO: Print installed module name and version as INFO.

        if self.is_work_dir_removed:
            shutil.rmtree(work_dir)
            Log.info("Removed working directory '{0}'".format(work_dir))
        else:
            Log.info("Saved working directory '{0}'".format(work_dir))

    def load_options_from_env(self):
        verbose = True if os.environ.get('VERBOSE') == 'true' else False
        # Set it as early as possible for other functions.
        self.verbose = verbose
        Log.verbose = verbose

        # Python's path that the module is installed on.
        python_path = sys.executable

        # Linked rpm's path. Default: rpm.
        rpm_path = os.environ.get('RPM', 'rpm')
        rpm_path = Cmd.which(rpm_path)

        # Installed RPM Python module's version.
        # Default: Same version with rpm.
        rpm_py_version = None
        if 'RPM_PY_VERSION' in os.environ:
            rpm_py_version = os.environ.get('RPM_PY_VERSION')
        else:
            stdout = Cmd.sh_e_out('{0} --version'.format(rpm_path))
            rpm_py_version = stdout.split()[2]

        # Command options
        setup_py_opts = '-q'
        curl_opts = '--silent'
        if verbose:
            setup_py_opts = '-v'
            curl_opts = ''

        is_work_dir_removed = True
        if 'WORK_DIR_REMOVED' in os.environ:
            if os.environ.get('WORK_DIR_REMOVED') == 'true':
                is_work_dir_removed = True
            else:
                is_work_dir_removed = False

        self.python_path = python_path
        self.rpm_path = rpm_path
        self.rpm_py_version = rpm_py_version
        self.setup_py_opts = setup_py_opts
        self.curl_opts = curl_opts
        self.is_work_dir_removed = is_work_dir_removed

    def verify_system_status(self):
        if not sys.platform.startswith('linux'):
            raise InstallError('Supported platform is Linux only.')

        if self.is_system_python():
            if self.is_python_binding_installed():
                message = (
                    'RPM Python binding already installed on system Python. '
                    'Nothing to do.'
                )
                Log.info(message)
                raise InstallSkipError(message)
            else:
                message = (
                    'RPM Python binding on system Python should be installed '
                    'by "dnf install python{,2,3}-rpm" manually.'
                )
                raise InstallError(message)

        if self.is_system_rpm():
            missing_packages = []
            # rpm-libs is required for /usr/lib64/librpm*.so
            # rpm-devel is required for /usr/lib64/pkgconfig/rpm.pc
            for package_name in ('rpm-libs', 'rpm-devel'):
                if not self.is_rpm_package_installed(package_name):
                    missing_packages.append(package_name)
            if missing_packages:
                comma_packages = ', '.join(missing_packages)
                space_packages = ' '.join(missing_packages)
                message = 'Required RPM not installed: [{0}].\n'.format(
                    comma_packages
                )
                message += 'Install it by "dnf install {0}".\n'.format(
                    space_packages
                )
                raise InstallError(message)

    @property
    def rpm_archive_top_dir(self):
        top_dir = self.RPM_ARCHIVE_TOP_DIR_FORMAT.format(
            version=self.rpm_py_version
        )
        return top_dir

    def download_and_expand_rpm_py(self):
        archive_url = self.RPM_ARCHIVE_URL_FORMAT.format(
            version=self.rpm_py_version
        )
        Log.info("Downloading archive '{0}' in the working directory.".format(
                 archive_url))
        if not Cmd.which('curl'):
            raise InstallError('curl not found. Install curl.')
        Cmd.sh_e('curl --location {0} "{1}" | tar xz'.format(
                 self.curl_opts, archive_url))

    def make_setup_py(self):
        replaced_word_dict = {
            '@PACKAGE_NAME@': 'rpm',
            '@VERSION@': self.rpm_py_version,
            '@PACKAGE_BUGREPORT@': 'rpm-maint@lists.rpm.org',
        }

        with open('setup.py.in') as f_in:
            with open('setup.py', 'w') as f_out:
                for line in f_in:
                    for key in replaced_word_dict:
                        line = line.replace(key, replaced_word_dict[key])
                    f_out.write(line)

    def install_rpm_py(self):
        self.make_setup_py()
        Cmd.sh_e('{0} setup.py {1} build'.format(self.python_path,
                                                 self.setup_py_opts))
        Cmd.sh_e('{0} setup.py {1} install'.format(self.python_path,
                                                   self.setup_py_opts))

    def is_system_python(self):
        return self.python_path.startswith('/usr/bin/python')

    def is_system_rpm(self):
        return self.rpm_path.startswith('/usr/bin/rpm')

    def is_python_binding_installed(self):
        cmd = '{0} -m pip --version'.format(self.python_path)
        pip_version_out = Cmd.sh_e_out(cmd)
        pip_version = pip_version_out.split()[1]
        Log.debug('Pip version: {0}'.format(pip_version))
        pip_major_version = int(pip_version.split('.')[0])

        installed = False
        # --format is from pip v9.0.0
        # https://pip.pypa.io/en/stable/news/
        if pip_major_version >= 9:
            cmd = '{0} -m pip list --format json'.format(self.python_path)
            json_str = Cmd.sh_e_out(cmd)
            json_obj = json.loads(json_str)

            for package in json_obj:
                Log.debug('pip list: {0}'.format(package))
                if package['name'] in ('rpm-python', 'rpm'):
                    installed = True
                    Log.debug('Package installed: {0}, {1}'.format(
                              package['name'], package['version']))
                    break
        else:
            # Implementation for pip old version.
            # It will be removed in the future.
            cmd = '{0} -m pip list'.format(self.python_path)
            out = Cmd.sh_e_out(cmd)
            lines = out.split('\n')
            for line in lines:
                if re.match('^rpm(-python)? ', line):
                    installed = True
                    Log.debug('Package installed.')
                    break

        return installed

    def is_rpm_package_installed(self, package_name):
        installed = True
        try:
            Cmd.sh_e('{0} --query {1} --quiet'.format(self.rpm_path,
                                                      package_name))
        except subprocess.CalledProcessError as e:
            installed = False
        return installed


class InstallError(Exception):
    pass


class InstallSkipError(Exception):
    pass


class Cmd(object):
    @classmethod
    def sh_e(cls, cmd, **kwargs):
        Log.debug('CMD: {0}'.format(cmd))
        cmd_kwargs = {
            'shell': True,
        }
        cmd_kwargs.update(kwargs)

        env = os.environ.copy()
        # Better to parse English output
        env['LC_ALL'] = 'en_US.utf-8'
        if 'env' in kwargs:
            env.update(kwargs['env'])
        cmd_kwargs['env'] = env

        proc = None
        try:
            proc = subprocess.Popen(cmd, **cmd_kwargs)
            stdout, stderr = proc.communicate()
            returncode = proc.returncode
            if returncode != 0:
                message = 'CMD: [{0}], Return Code: [{1}] at [{2}]'.format(
                    cmd, returncode, os.getcwd())
                if stderr is not None:
                    message += ' Stderr: [{0}]'.format(stderr)
                Log.error(message)
                raise InstallError(message)

            if stdout is not None:
                stdout = stdout.decode('ascii')
            return stdout
        except Exception as e:
            try:
                proc.kill()
            except:
                pass
            raise e

    @classmethod
    def sh_e_out(cls, cmd, **kwargs):
        cmd_kwargs = {
            'stdout': subprocess.PIPE,
        }
        cmd_kwargs.update(kwargs)
        return cls.sh_e(cmd, **cmd_kwargs)

    @classmethod
    def cd(cls, directory):
        Log.debug('CMD: cd {0}'.format(directory))
        os.chdir(directory)

    @classmethod
    @contextmanager
    def pushd(cls, new_dir):
        previous_dir = os.getcwd()
        try:
            new_ab_dir = None
            if os.path.isabs(new_dir):
                new_ab_dir = new_dir
            else:
                new_ab_dir = os.path.join(previous_dir, new_dir)
            # Use absolute path to show it on FileNotFoundError message.
            cls.cd(new_ab_dir)
            yield
        finally:
            cls.cd(previous_dir)

    @classmethod
    def which(cls, cmd):
        abs_path_cmd = None
        if sys.version_info >= (3, 3):
            abs_path_cmd = shutil.which(cmd)
        else:
            abs_path_cmd = cls.sh_e_out('which {0}'.format(cmd))
            abs_path_cmd = abs_path_cmd.rstrip()
        return abs_path_cmd


class Log(object):
    # Class variable
    verbose = False

    @classmethod
    def error(cls, message):
        print('[ERROR] {0}'.format(message))

    @classmethod
    def info(cls, message):
        print('[INFO] {0}'.format(message))

    @classmethod
    def debug(cls, message):
        if cls.verbose:
            print('[DEBUG] {0}'.format(message))


def main():
    Log.info('Installing...')
    app = Application()
    app.run()
    Log.info("Done successfully.")


if __name__ == '__main__':
    main()
