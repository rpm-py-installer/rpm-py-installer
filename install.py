import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from distutils.spawn import find_executable


class Application(object):
    RPM_GIT_REPO_BASE_URL = 'https://github.com/rpm-software-management/rpm'
    RPM_GIT_REPO_URL = '{0}.git'.format(RPM_GIT_REPO_BASE_URL)
    RPM_ARCHIVE_URL_FORMAT = (
        RPM_GIT_REPO_BASE_URL + '/archive/{tag_name}.tar.gz'
    )
    RPM_ARCHIVE_TOP_DIR_NAME_FORMAT = 'rpm-{tag_name}'

    def __init__(self):
        self.load_options_from_env()

    def run(self):
        try:
            self.verify_system_status()
        except InstallSkipError:
            Log.info('Install skipped.')
            return

        work_dir = tempfile.mkdtemp(suffix='-rpm-py-installer')
        Log.info("Created working directory '{0}'".format(work_dir))

        with Cmd.pushd(work_dir):
            top_dir_name = self.download_and_expand_rpm_py()
            rpm_py_dir = os.path.join(top_dir_name, 'python')
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

        # Git branch name. Default: None
        git_branch = None
        if 'GIT_BRANCH' in os.environ:
            git_branch = os.environ.get('GIT_BRANCH')

        # Use optimized setup.py?
        # Default: true
        setup_py_optimized = True
        if 'SETUP_PY_OPTM' in os.environ:
            if os.environ.get('SETUP_PY_OPTM') == 'true':
                setup_py_optimized = True
            else:
                setup_py_optimized = False

        # Command options
        setup_py_opts = '-q'
        if verbose:
            setup_py_opts = '-v'

        is_work_dir_removed = True
        if 'WORK_DIR_REMOVED' in os.environ:
            if os.environ.get('WORK_DIR_REMOVED') == 'true':
                is_work_dir_removed = True
            else:
                is_work_dir_removed = False

        self.python_path = python_path
        self.rpm_path = rpm_path
        self.rpm_py_version = rpm_py_version
        self.git_branch = git_branch
        self.setup_py_optimized = setup_py_optimized
        self.setup_py_opts = setup_py_opts
        self.is_work_dir_removed = is_work_dir_removed

    @property
    def rpm_py_version_info(self):
        version_str = self.rpm_py_version
        version_info_list = re.findall(r'[0-9a-zA-Z]+', version_str)
        return tuple(version_info_list)

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

    def get_rpm_archive_top_dir_name(self, tag_name):
        top_dir = self.RPM_ARCHIVE_TOP_DIR_NAME_FORMAT.format(
            tag_name=tag_name
        )
        return top_dir

    def download_and_expand_rpm_py(self):
        top_dir_name = None
        if self.git_branch:
            # Download a source by git clone.
            top_dir_name = self.download_and_expand_by_git()
        else:
            # Download a source from the arcihve URL.
            # Downloading the compressed archive is better than "git clone",
            # because it is faster.
            # If download failed due to URL not found, try "git clone".
            try:
                top_dir_name = self.download_and_expand_from_archive_url()
            except ArchiveNotFoundError:
                Log.info('Try to download by git clone.')
                top_dir_name = self.download_and_expand_by_git()
        return top_dir_name

    def download_and_expand_from_archive_url(self):
        tag_names = self.predict_candidate_git_tag_names()
        tar_gz_file_name = None

        tag_name_len = len(tag_names)
        decided_tag_name = None
        for index, tag_name in enumerate(tag_names):
            archive_url = self.RPM_ARCHIVE_URL_FORMAT.format(
                                                      tag_name=tag_name)
            Log.info("Downloading archive. '{0}'.".format(archive_url))
            try:
                tar_gz_file_name = Cmd.curl_remote_name(archive_url)
            except ArchiveNotFoundError as e:
                Log.info('Archive not found. URL: {0}'.format(archive_url))
                if index + 1 < tag_name_len:
                    Log.info('Try to download next candidate URL.')
                else:
                    raise e
            else:
                decided_tag_name = tag_name
                break

        Cmd.tar_xzf(tar_gz_file_name)

        top_dir_name = self.get_rpm_archive_top_dir_name(decided_tag_name)
        return top_dir_name

    def download_and_expand_by_git(self):
        self.do_git_clone()
        return 'rpm'

    def predict_candidate_git_tag_names(self):
        version = self.rpm_py_version
        name_release = 'rpm-{0}-release'.format(version)
        name_non_release = 'rpm-{0}'.format(version)
        tag_names = None
        # version string: N.N.N.N is for release.
        if re.match(r'^[\d.]+$', version):
            tag_names = [
                name_release,
                name_non_release,
            ]
        else:
            tag_names = [
                name_non_release,
                name_release,
            ]
        return tag_names

    def do_git_clone(self):
        if not Cmd.which('git'):
            raise InstallError('git command not found. Install git.')

        branch = None
        if self.git_branch:
            branch = self.git_branch
        else:
            branch = self.predict_git_branch()

        git_clone_cmd = 'git clone -b {branch} --depth=1 {repo_url}'.format(
            branch=branch,
            repo_url=self.RPM_GIT_REPO_URL,
        )
        Log.info("Downloading source by git clone. 'branch: {0}'".format(
                 branch))
        Cmd.sh_e(git_clone_cmd)

    def predict_git_branch(self):
        git_branch = None

        version_info = self.rpm_py_version_info
        stable_branch = 'rpm-{major}.{minor}.x'.format(
            major=version_info[0],
            minor=version_info[1],
        )
        git_ls_remote_cmd = 'git ls-remote --heads {repo_url} {branch}'.format(
            repo_url=self.RPM_GIT_REPO_URL,
            branch=stable_branch,
        )
        stdout = Cmd.sh_e_out(git_ls_remote_cmd)
        if stable_branch in stdout:
            git_branch = stable_branch
        else:
            git_branch = 'master'

        return git_branch

    def make_setup_py(self):
        replaced_word_dict = {
            '@PACKAGE_NAME@': 'rpm',
            '@VERSION@': self.rpm_py_version,
            '@PACKAGE_BUGREPORT@': 'rpm-maint@lists.rpm.org',
        }
        patches = [
            # Use setuptools to prevent deprecation message when uninstalling.
            # https://github.com/rpm-software-management/rpm/pull/323
            {
                'src': '^from distutils.core import setup, Extension *\n$',
                'dest': '''
import sys
if sys.version_info >= (3, 0):
    try:
        from setuptools import setup, Extension
    except ImportError:
        from distutils.core import setup, Extension
else:
    from distutils.core import setup, Extension
'''
            },
        ]

        with open('setup.py.in') as f_in:
            with open('setup.py', 'w') as f_out:
                for line in f_in:
                    for key in replaced_word_dict:
                        line = line.replace(key, replaced_word_dict[key])

                    if self.setup_py_optimized:
                        for patch in patches:
                            if re.match(patch['src'], line):
                                line = patch['dest']
                                patch['matched'] = True

                    f_out.write(line)
        for patch in patches:
            if 'matched' not in patch or not patch['matched']:
                Log.warn('Patch not applied {0}'.format(patch['src']))

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
        except InstallError:
            installed = False
        return installed


class InstallError(Exception):
    pass


class InstallSkipError(Exception):
    pass


class ArchiveNotFoundError(Exception):
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
            abs_path_cmd = find_executable(cmd)
        return abs_path_cmd

    @classmethod
    def curl_remote_name(cls, file_url):
        """A command that behaves like "curl --remote-name".

        Raise HTTPError if the file_url not found.
        """
        tar_gz_file_name = file_url.split('/')[-1]

        if sys.version_info >= (3, 2):
            from urllib.request import urlopen
            from urllib.error import HTTPError
        else:
            from urllib2 import urlopen
            from urllib2 import HTTPError

        response = None
        try:
            response = urlopen(file_url)
        except HTTPError as e:
            message = 'Download failed: URL: {0}, reason: {1}'.format(
                      file_url, e)
            if 'HTTP Error 404' in str(e):
                raise ArchiveNotFoundError(message)
            else:
                raise InstallError(message)

        tar_gz_file_obj = io.BytesIO(response.read())
        with open(tar_gz_file_name, 'wb') as f_out:
            f_out.write(tar_gz_file_obj.read())
        return tar_gz_file_name

    @classmethod
    def tar_xzf(cls, tar_gz_file_path):
        """A command like "tar xzf tar_gz_file_path".

        Raise tarfile.ReadError if the file is broken.
        """
        try:
            with tarfile.open(tar_gz_file_path) as tar:
                tar.extractall()
        except tarfile.ReadError as e:
            message_format = (
                'Extract failed: '
                'tar_gz_file_path: {0}, reason: {1}'
            )
            raise InstallError(message_format.format(tar_gz_file_path, e))


class Log(object):
    # Class variable
    verbose = False

    @classmethod
    def error(cls, message):
        print('[ERROR] {0}'.format(message))

    @classmethod
    def warn(cls, message):
        print('[WARN] {0}'.format(message))

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
