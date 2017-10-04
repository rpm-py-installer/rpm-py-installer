"""Classes for all of install.

Import only standard modules to run install.py directly.
"""
import fnmatch
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
    """A class for main applicaton logic."""

    def __init__(self):
        """Initialize this class."""
        self._load_options_from_env()

    def run(self):
        """Run install process."""
        try:
            self._verify_system_status()
        except InstallSkipError:
            Log.info('Install skipped.')
            return

        work_dir = tempfile.mkdtemp(suffix='-rpm-py-installer')
        Log.info("Created working directory '{0}'".format(work_dir))

        with Cmd.pushd(work_dir):
            self.rpm_py.download_and_install()
            if not self.python.is_python_binding_installed():
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

    def _load_options_from_env(self):
        verbose = True if os.environ.get('VERBOSE') == 'true' else False
        # Set it as early as possible for other functions.
        self.verbose = verbose
        Log.verbose = verbose

        # Python's path that the module is installed on.
        python = Python()

        # Linked rpm's path. Default: rpm.
        rpm_path = os.environ.get('RPM', 'rpm')
        rpm_path = Cmd.which(rpm_path)
        if not rpm_path:
            raise InstallError('rpm command not found. Install rpm.')
        rpm = Rpm(rpm_path)

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
        optimized = True
        if 'RPM_PY_OPTM' in os.environ:
            if os.environ.get('RPM_PY_OPTM') == 'true':
                optimized = True
            else:
                optimized = False

        is_work_dir_removed = True
        if 'WORK_DIR_REMOVED' in os.environ:
            if os.environ.get('WORK_DIR_REMOVED') == 'true':
                is_work_dir_removed = True
            else:
                is_work_dir_removed = False

        self.python = python
        self.rpm = rpm
        self.rpm_py = RpmPy(rpm_py_version, python, rpm,
                            git_branch=git_branch,
                            optimized=optimized,
                            verbose=verbose)
        self.is_work_dir_removed = is_work_dir_removed

    def _verify_system_status(self):
        if not sys.platform.startswith('linux'):
            raise InstallError('Supported platform is Linux only.')

        if self.python.is_system_python():
            if self.python.is_python_binding_installed():
                message = '''
RPM Python binding already installed on system Python.
Nothing to do.
'''
                Log.info(message)
                raise InstallSkipError(message)
            else:
                message = '''
RPM Python binding on system Python should be installed manually.
Install the proper RPM package of python{,2,3}-rpm.
'''
                raise InstallError(message)

        if self.rpm.is_system_rpm():
            self._verify_rpm_package_status()

    def _verify_rpm_package_status(self):
        # rpm-libs is required for /usr/lib64/librpm*.so
        self.rpm.verify_packages_installed(['rpm-libs'])

        is_rpm_build_libs = self.rpm.is_package_installed('rpm-build-libs')
        if not is_rpm_build_libs and not self.rpm.is_downloadable():
            message = '''
RPM: rpm-build-libs or
RPM download tool (dnf-plugins-core (dnf) or yum-utils (yum)) required.
Install any of those.
'''.format(self.rpm.package_cmd)
            raise InstallError(message)


class RpmPy(object):
    """A class for RPM Python binding."""

    def __init__(self, version, python, rpm, **kwargs):
        """Initialize this class."""
        if not version:
            raise ValueError('version required.')
        if not python:
            raise ValueError('python required.')
        if not rpm:
            raise ValueError('rpm required.')

        git_branch = kwargs.get('git_branch')
        optimized = kwargs.get('optimized', True)
        verbose = kwargs.get('verbose', False)

        rpm_py_version = RpmPyVersion(version)

        self.version = rpm_py_version
        self.downloader = Downloader(rpm_py_version, git_branch=git_branch)
        self.installer = Installer(rpm_py_version, python, rpm,
                                   optimized=optimized,
                                   verbose=verbose)

    def download_and_install(self):
        """Download and install RPM Python binding."""
        top_dir_name = self.downloader.download_and_expand()
        rpm_py_dir = os.path.join(top_dir_name, 'python')
        Cmd.cd(rpm_py_dir)
        self.installer.run()


class RpmPyVersion(object):
    """A class to manage RPM Python binding version."""

    def __init__(self, version, **kwargs):
        """Initialize this class."""
        if not version:
            ValueError('version required.')
        self.version = version

    def __str__(self):
        """Return the string expression of this class."""
        return self.version

    @property
    def info(self):
        """RPM Python binding's version info.

        tuple object. ex. ('4', '14', '0', 'rc1')
        """
        version_str = self.version
        version_info_list = re.findall(r'[0-9a-zA-Z]+', version_str)
        return tuple(version_info_list)


class SetupPy(object):
    """A class for the RPM Python binding's setup.py file.

    It does parsing and patching for setup.py file.
    """

    DEFAULT_PATCHES = [
        # Use setuptools to prevent deprecation message when uninstalling.
        # https://github.com/rpm-software-management/rpm/pull/323
        {
            'src': r'\nfrom distutils.core import setup, Extension *?\n',
            'dest': '''
import sys
if sys.version_info >= (3, 0):
    try:
        from setuptools import setup, Extension
    except ImportError:
        from distutils.core import setup, Extension
else:
    from distutils.core import setup, Extension
''',
            'required': True,
        },
    ]
    IN_PATH = 'setup.py.in'
    OUT_PATH = 'setup.py'

    def __init__(self, version, **kwargs):
        """Initialize this class."""
        if not version:
            ValueError('version required.')
        if not isinstance(version, RpmPyVersion):
            ValueError('version invalid instance.')
        self.version = version
        self.replaced_word_dict = {
            '@PACKAGE_NAME@': 'rpm',
            '@VERSION@': version.version,
            '@PACKAGE_BUGREPORT@': 'rpm-maint@lists.rpm.org',
        }
        optimized = kwargs.get('optimized', True)
        patches = []
        if optimized:
            patches = self.DEFAULT_PATCHES
        self.patches = patches

    def add_patchs_to_build_without_pkg_config(self, lib_dir, include_dir):
        """Add patches to remove pkg-config command and rpm.pc part.

        Replace with given library_path: lib_dir and include_path: include_dir
        without rpm.pc file.
        """
        additional_patches = [
            {
                'src': r"pkgconfig\('--libs-only-L'\)",
                'dest': "['{0}']".format(lib_dir),
            },
            # Considering -libs-only-l and -libs-only-L
            # https://github.com/rpm-software-management/rpm/pull/327
            {
                'src': r"pkgconfig\('--libs(-only-l)?'\)",
                'dest': "['rpm', 'rpmio']",
                'required': True,
            },
            {
                'src': r"pkgconfig\('--cflags'\)",
                'dest': "['{0}']".format(include_dir),
                'required': True,
            },
        ]
        self.patches.extend(additional_patches)

    def apply_and_save(self):
        """Apply replaced words and patches, and save setup.py file."""
        patches = self.patches

        content = None
        with open(self.IN_PATH) as f_in:
            # As setup.py.in file size is 2.4 KByte.
            # it's fine to read entire content.
            content = f_in.read()

        # Replace words.
        for key in self.replaced_word_dict:
            content = content.replace(key, self.replaced_word_dict[key])

        # Apply patches.
        out_patches = []
        for patch in patches:
            pattern = re.compile(patch['src'], re.MULTILINE)
            (content, subs_num) = re.subn(pattern, patch['dest'],
                                          content)
            if subs_num > 0:
                patch['applied'] = True
            out_patches.append(patch)

        for patch in out_patches:
            if patch.get('required') and not patch.get('applied'):
                Log.warn('Patch not applied {0}'.format(patch['src']))

        with open(self.OUT_PATH, 'w') as f_out:
            f_out.write(content)

        self.pathces = out_patches
        # Release content data to make it released by GC quickly.
        content = None


class Downloader(object):
    """A class to download RPM Python binding."""

    RPM_GIT_REPO_BASE_URL = 'https://github.com/rpm-software-management/rpm'
    RPM_GIT_REPO_URL = '{0}.git'.format(RPM_GIT_REPO_BASE_URL)
    RPM_ARCHIVE_URL_FORMAT = (
        RPM_GIT_REPO_BASE_URL + '/archive/{tag_name}.tar.gz'
    )
    RPM_ARCHIVE_TOP_DIR_NAME_FORMAT = 'rpm-{tag_name}'

    def __init__(self, rpm_py_version, **kwargs):
        """Initialize this class."""
        if not rpm_py_version:
            ValueError('rpm_py_version required.')
        if not isinstance(rpm_py_version, RpmPyVersion):
            ValueError('rpm_py_version invalid instance.')

        self.rpm_py_version = rpm_py_version
        self.git_branch = kwargs.get('git_branch')

    def download_and_expand(self):
        """Download and expand RPM Python binding."""
        top_dir_name = None
        if self.git_branch:
            # Download a source by git clone.
            top_dir_name = self._download_and_expand_by_git()
        else:
            # Download a source from the arcihve URL.
            # Downloading the compressed archive is better than "git clone",
            # because it is faster.
            # If download failed due to URL not found, try "git clone".
            try:
                top_dir_name = self._download_and_expand_from_archive_url()
            except ArchiveNotFoundError:
                Log.info('Try to download by git clone.')
                top_dir_name = self._download_and_expand_by_git()
        return top_dir_name

    def _get_rpm_archive_top_dir_name(self, tag_name):
        top_dir = self.RPM_ARCHIVE_TOP_DIR_NAME_FORMAT.format(
            tag_name=tag_name
        )
        return top_dir

    def _download_and_expand_from_archive_url(self):
        tag_names = self._predict_candidate_git_tag_names()
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

        top_dir_name = self._get_rpm_archive_top_dir_name(decided_tag_name)
        return top_dir_name

    def _download_and_expand_by_git(self):
        self._do_git_clone()
        return 'rpm'

    def _predict_candidate_git_tag_names(self):
        version = self.rpm_py_version.version
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

    def _do_git_clone(self):
        if not Cmd.which('git'):
            raise InstallError('git command not found. Install git.')

        branch = None
        if self.git_branch:
            branch = self.git_branch
        else:
            branch = self._predict_git_branch()

        git_clone_cmd = 'git clone -b {branch} --depth=1 {repo_url}'.format(
            branch=branch,
            repo_url=self.RPM_GIT_REPO_URL,
        )
        Log.info("Downloading source by git clone. 'branch: {0}'".format(
                 branch))
        Cmd.sh_e(git_clone_cmd)

    def _predict_git_branch(self):
        git_branch = None

        version_info = self.rpm_py_version.info
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


class Installer(object):
    """A class to install RPM Python binding."""

    def __init__(self, rpm_py_version, python, rpm, **kwargs):
        """Initialize this class."""
        if not rpm_py_version:
            ValueError('rpm_py_version required.')
        if not python:
            ValueError('python required.')
        if not rpm:
            ValueError('rpm required.')
        if not isinstance(rpm_py_version, RpmPyVersion):
            ValueError('rpm_py_version invalid instance.')
        if not isinstance(python, Python):
            ValueError('python invalid instance.')
        if not isinstance(rpm, Rpm):
            ValueError('rpm invalid instance.')

        optimized = kwargs.get('optimized', True)
        verbose = kwargs.get('verbose', False)

        self.rpm_py_version = rpm_py_version
        self.python = python
        self.rpm = rpm
        self.setup_py = SetupPy(rpm_py_version, optimized=optimized)
        self.setup_py_opts = '-v' if verbose else '-q'
        self.optimized = optimized

    def run(self):
        """Run install main logic."""
        try:
            if not self._is_rpm_devel_installed():
                self._prepare_so_files()
                self._prepare_include_files()
                self._prepare_dependency_so_include_files()
                self.setup_py.add_patchs_to_build_without_pkg_config(
                    self.rpm.lib_dir, self.rpm.include_dir
                )
            self.setup_py.apply_and_save()
            self._build_and_install()
        except InstallError as e:
            if not self._is_rpm_devel_installed():
                org_message = str(e)
                message = '''
Install failed without rpm-devel package by below reason.
Can you install the RPM package, and run this installer again?
'''
                message += org_message
                raise InstallError(message)
            else:
                raise e

    def _is_rpm_build_libs_installed(self):
        return self.rpm.is_package_installed('rpm-build-libs')

    def _is_rpm_devel_installed(self):
        return self.rpm.is_package_installed('rpm-devel')

    def _is_popt_devel_installed(self):
        return self.rpm.is_package_installed('popt-devel')

    def _prepare_so_files(self):
        build_link_dir = None

        if self.rpm.is_downloadable():
            if self._is_rpm_build_libs_installed():
                build_link_dir = self.rpm.lib_dir
            else:
                self.rpm.download_and_extract('rpm-build-libs')
                current_dir = os.getcwd()
                build_link_dir = current_dir + self.rpm.lib_dir
        else:
            if not self._is_rpm_build_libs_installed():
                message = '''
Required RPM not installed: [rpm-build-libs],
when a RPM download plugin not installed.
'''
                raise InstallError(message)
            build_link_dir = self.rpm.lib_dir

        so_dicts = [
            {
                'name': 'rpmio',
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'rpmio/.libs',
            },
            {
                'name': 'rpm',
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'lib/.libs',
            },
            {
                'name': 'rpmbuild',
                'sym_src_dir': build_link_dir,
                'sym_dst_dir': 'build/.libs',
            },
            {
                'name': 'rpmsign',
                'sym_src_dir': build_link_dir,
                'sym_dst_dir': 'sign/.libs',
            },
        ]

        for so_dict in so_dicts:
            pattern = 'lib{0}.so*'.format(so_dict['name'])
            so_files = Cmd.find(so_dict['sym_src_dir'], pattern)
            if not so_files:
                message = 'so file pattern {0} not found at {1}'.format(
                    pattern, so_dict['sym_src_dir']
                )
                raise InstallError(message)
            sym_dst_dir = os.path.abspath('../{0}'.format(
                                           so_dict['sym_dst_dir']))
            if not os.path.isdir(sym_dst_dir):
                Cmd.mkdir_p(sym_dst_dir)

            cmd = 'ln -sf {0} {1}/lib{2}.so'.format(so_files[0],
                                                    sym_dst_dir,
                                                    so_dict['name'])
            Cmd.sh_e(cmd)

    def _prepare_include_files(self):
        src_header_dirs = [
            'rpmio',
            'lib',
            'build',
            'sign',
        ]
        with Cmd.pushd('..'):
            src_include_dir = os.path.abspath('./include')
            for header_dir in src_header_dirs:
                header_files = Cmd.find(header_dir, '*.h')
                for header_file in header_files:
                    pattern = '^{0}/'.format(header_dir)
                    (dst_header_file, subs_num) = re.subn(pattern,
                                                          '', header_file)
                    if subs_num == 0:
                        message = 'Failed to replace header_file: {0}'.format(
                            header_file)
                        raise ValueError(message)
                    dst_header_file = os.path.abspath(
                        os.path.join(src_include_dir, 'rpm', dst_header_file)
                    )
                    dst_dir = os.path.dirname(dst_header_file)
                    if not os.path.isdir(dst_dir):
                        Cmd.mkdir_p(dst_dir)
                    shutil.copyfile(header_file, dst_header_file)

    def _prepare_dependency_so_include_files(self):
        """Prepare build dependency's so and include files.

        - popt-devel
        """
        if self._has_dependency_rpm_popt_devel():
            if self._is_popt_devel_installed():
                pass
            elif self.rpm.is_downloadable():
                if not self.rpm.is_package_installed('popt'):
                    message = '''
Required RPM not installed: [popt],
'''
                    raise InstallError(message)

                self.rpm.download_and_extract('popt-devel')

                # Copy libpopt.so to rpm_root/lib/.libs/.
                pattern = 'libpopt.so*'
                so_files = Cmd.find(self.rpm.lib_dir, pattern)
                if not so_files:
                    message = 'so file pattern {0} not found at {1}'.format(
                        pattern, self.rpm.lib_dir
                    )
                    raise InstallError(message)
                cmd = 'ln -sf {0} ../lib/.libs/libpopt.so'.format(
                      so_files[0])
                Cmd.sh_e(cmd)

                # Copy popt.h to rpm_root/include
                shutil.copy('./usr/include/popt.h', '../include')
            else:
                message = '''
Required RPM not installed: [popt-devel],
when a RPM download plugin not installed.
'''
                raise InstallError(message)

    def _build_and_install(self):
        python_path = self.python.python_path
        Cmd.sh_e('{0} setup.py {1} build'.format(python_path,
                                                 self.setup_py_opts))
        Cmd.sh_e('{0} setup.py {1} install'.format(python_path,
                                                   self.setup_py_opts))

    def _has_dependency_rpm_popt_devel(self):
        found = False
        with open('../include/rpm/rpmlib.h') as f_in:
            for line in f_in:
                if re.match(r'^#include .*popt.h.*$', line):
                    found = True
                    break
        return found


class Python(object):
    """A class for Python environment."""

    def __init__(self, python_path=sys.executable):
        """Initialize this class."""
        self.python_path = python_path

    def is_system_python(self):
        """Check if the Python is system Python."""
        return self.python_path.startswith('/usr/bin/python')

    def is_python_binding_installed(self):
        """Check if the Python binding module has already installed."""
        pip_version = self._get_pip_version()
        Log.debug('Pip version: {0}'.format(pip_version))
        pip_major_version = int(pip_version.split('.')[0])

        installed = False
        # --format is from pip v9.0.0
        # https://pip.pypa.io/en/stable/news/
        if pip_major_version >= 9:
            json_obj = self._get_pip_list_json_obj()

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
            lines = self._get_pip_list_lines()
            for line in lines:
                if re.match('^rpm(-python)? ', line):
                    installed = True
                    Log.debug('Package installed.')
                    break

        return installed

    def _get_pip_version(self):
        cmd = '{0} -m pip --version'.format(self.python_path)
        pip_version_out = Cmd.sh_e_out(cmd)
        pip_version = pip_version_out.split()[1]
        return pip_version

    def _get_pip_list_json_obj(self):
        cmd = '{0} -m pip list --format json'.format(self.python_path)
        json_str = Cmd.sh_e_out(cmd)
        json_obj = json.loads(json_str)
        return json_obj

    def _get_pip_list_lines(self):
        cmd = '{0} -m pip list'.format(self.python_path)
        out = Cmd.sh_e_out(cmd)
        lines = out.split('\n')
        return lines


class Rpm(object):
    """A class for RPM environment including DNF and Yum."""

    def __init__(self, rpm_path):
        """Initialize this class."""
        is_dnf = True if Cmd.which('dnf') else False

        self.rpm_path = rpm_path
        self.is_dnf = is_dnf
        self.arch = Cmd.sh_e_out('uname -m').rstrip()
        self._lib_dir = None

    def is_system_rpm(self):
        """Check if the RPM is system RPM."""
        return self.rpm_path.startswith('/usr/bin/rpm')

    def is_package_installed(self, package_name):
        """Check if the RPM package is installed."""
        if not package_name:
            raise ValueError('package_name required.')

        installed = True
        try:
            Cmd.sh_e('{0} --query {1} --quiet'.format(self.rpm_path,
                                                      package_name))
        except InstallError:
            installed = False
        return installed

    def verify_packages_installed(self, package_names):
        """Check if the RPM packages are installed.

        Raise InstallError if any of the packages is not installed.
        """
        if not package_names:
            raise ValueError('package_names required.')

        missing_packages = []
        for package_name in package_names:
            if not self.is_package_installed(package_name):
                missing_packages.append(package_name)

        if missing_packages:
            comma_packages = ', '.join(missing_packages)
            message = '''
Required RPM not installed: [{0}].
Install the RPM package.
'''.format(comma_packages)
            raise InstallError(message)

    @property
    def lib_dir(self):
        """Return standard library directory path used by RPM libs.

        TODO: Support non-system RPM.
        """
        if not self._lib_dir:
            rpm_lib_dir = None
            cmd = '{0} -ql rpm-libs'.format(self.rpm_path)
            out = Cmd.sh_e_out(cmd)
            lines = out.split('\n')
            for line in lines:
                if 'librpm.so' in line:
                    rpm_lib_dir = os.path.dirname(line)
                    break
            self._lib_dir = rpm_lib_dir
        return self._lib_dir

    @property
    def include_dir(self):
        """Return include directory.

        TODO: Support non-system RPM.
        """
        return '/usr/include'

    @property
    def package_cmd(self):
        """Return package command name. dnf/yum."""
        cmd = 'dnf' if self.is_dnf else 'yum'
        return cmd

    def is_downloadable(self):
        """Return if rpm is downloadable by the package command.

        Check if dnf or yum plugin package exists.
        """
        is_plugin_avaiable = False
        if self.is_dnf:
            is_plugin_avaiable = self.is_package_installed(
                                 'dnf-plugins-core')
        else:
            """ yum environment.
            Make sure
            # yum -y --downloadonly --downloaddir=. install package_name
            is only available for root user.

            yumdownloader in yum-utils is available for normal user.
            https://access.redhat.com/solutions/10154
            """
            is_plugin_avaiable = self.is_package_installed(
                                 'yum-utils')
        return is_plugin_avaiable

    def download_and_extract(self, package_name):
        """Download and extract given package."""
        self.download(package_name)
        self.extract(package_name)

    def download(self, package_name):
        """Download given package."""
        if not package_name:
            ValueError('package_name required.')
        if self.is_dnf:
            cmd = 'dnf download {0}.{1}'.format(package_name, self.arch)
        else:
            cmd = 'yumdownloader {0}.{1}'.format(package_name, self.arch)
        Cmd.sh_e(cmd)

    def extract(self, package_name):
        """Extract given package."""
        for cmd in ['rpm2cpio', 'cpio']:
            if not Cmd.which(cmd):
                message = '{0} command not found. Install {0}.'.format(cmd)
                raise InstallError(message)

        pattern = '{0}*{1}.rpm'.format(package_name, self.arch)
        rpm_files = Cmd.find('.', pattern)
        if not rpm_files:
            raise InstallError('PRM file not found.')
        cmd = 'rpm2cpio {0} | cpio -idmv'.format(rpm_files[0])
        Cmd.sh_e(cmd)


class InstallError(Exception):
    """A exception class for general install error."""

    pass


class InstallSkipError(Exception):
    """A exception class for skipping the install process."""

    pass


class ArchiveNotFoundError(Exception):
    """A exception class RPM archive not found on the server."""

    pass


class Cmd(object):
    """A utility class like a UNIX command."""

    @classmethod
    def sh_e(cls, cmd, **kwargs):
        """Run the command. It behaves like "sh -e".

        It raises InstallError if the command failed.
        """
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
        # Capture stderr to show it on error message.
        cmd_kwargs['stderr'] = subprocess.PIPE

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
        """Run the command. and returns the stdout."""
        cmd_kwargs = {
            'stdout': subprocess.PIPE,
        }
        cmd_kwargs.update(kwargs)
        return cls.sh_e(cmd, **cmd_kwargs)

    @classmethod
    def cd(cls, directory):
        """Change directory. It behaves like "cd directory"."""
        Log.debug('CMD: cd {0}'.format(directory))
        os.chdir(directory)

    @classmethod
    @contextmanager
    def pushd(cls, new_dir):
        """Change directory, and back to previous directory.

        It behaves like "pushd directory; something; popd".
        """
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
        """Return an absolute path of the command.

        It behaves like "which command".
        """
        abs_path_cmd = None
        if sys.version_info >= (3, 3):
            abs_path_cmd = shutil.which(cmd)
        else:
            abs_path_cmd = find_executable(cmd)
        return abs_path_cmd

    @classmethod
    def curl_remote_name(cls, file_url):
        """Download file_url, and save as a file name of the URL.

        It behaves like "curl -O or --remote-name".
        It raises HTTPError if the file_url not found.
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
        """Extract tar.gz file.

        It behaves like "tar xzf tar_gz_file_path".
        it raises tarfile.ReadError if the file is broken.
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

    @classmethod
    def find(cls, searched_dir, pattern):
        """Find matched files.

        It does not include symbolic file in the result.
        """
        Log.debug('find {0} with pattern: {1}'.format(searched_dir, pattern))
        matched_files = []
        for root_dir, dir_names, file_names in os.walk(searched_dir,
                                                       followlinks=False):
            for file_name in file_names:
                if fnmatch.fnmatch(file_name, pattern):
                    file_path = os.path.join(root_dir, file_name)
                    if not os.path.islink(file_path):
                        matched_files.append(file_path)
        matched_files.sort()
        return matched_files

    @classmethod
    def mkdir_p(cls, path):
        """Make directory with recursively.

        It behaves like "mkdir -p directory_path".
        """
        os.makedirs(path)


class Log(object):
    """A class for logging."""

    # Class variable
    verbose = False

    @classmethod
    def error(cls, message):
        """Log a message with level ERROR."""
        print('[ERROR] {0}'.format(message))

    @classmethod
    def warn(cls, message):
        """Log a message with level WARN."""
        print('[WARN] {0}'.format(message))

    @classmethod
    def info(cls, message):
        """Log a message with level INFO."""
        print('[INFO] {0}'.format(message))

    @classmethod
    def debug(cls, message):
        """Log a message with level DEBUG.

        It does not log if verbose mode.
        """
        if cls.verbose:
            print('[DEBUG] {0}'.format(message))


def main():
    """Run main logic.

    It is called at first when install.py is called.
    """
    Log.info('Installing...')
    app = Application()
    app.run()
    Log.info("Done successfully.")


if __name__ == '__main__':
    main()
