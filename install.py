"""Classes for all of install.

Import only standard modules to run install.py directly.
"""
import contextlib
import fnmatch
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from distutils.spawn import find_executable
from distutils.sysconfig import get_python_lib


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
        verbose = True if os.environ.get('RPM_PY_VERBOSE') == 'true' else False
        # Set it as early as possible for other functions.
        self.verbose = verbose
        Log.verbose = verbose

        # Python's path that the module is installed on.
        python = Python()

        # Linked rpm's path. Default: rpm.
        rpm_path = os.environ.get('RPM_PY_RPM_BIN', 'rpm')
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
            rpm_py_version = rpm.version

        # Git branch name. Default: None
        git_branch = None
        if 'RPM_PY_GIT_BRANCH' in os.environ:
            git_branch = os.environ.get('RPM_PY_GIT_BRANCH')

        # Use optimized setup.py?
        # Default: true
        optimized = True
        if 'RPM_PY_OPTM' in os.environ:
            if os.environ.get('RPM_PY_OPTM') == 'true':
                optimized = True
            else:
                optimized = False

        is_work_dir_removed = True
        if 'RPM_PY_WORK_DIR_REMOVED' in os.environ:
            if os.environ.get('RPM_PY_WORK_DIR_REMOVED') == 'true':
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

        # Check RPM so files to build the Python binding.
        message_format = '''
RPM: {0} or
RPM download tool (dnf-plugins-core (dnf) or yum-utils (yum)) required.
Install any of those.
'''
        if self.rpm.has_sys_rpm_rpm_bulid_libs():
            if (not self.rpm.is_package_installed('rpm-build-libs')
               and not self.rpm.is_downloadable()):
                raise InstallError(message_format.format('rpm-build-libs'))
        else:
            # All the needed so files are included in rpm-libs package.
            pass


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

        setup_py_in_found = False
        with Cmd.pushd(rpm_py_dir):
            if self.installer.setup_py.exists_in_path():
                setup_py_in_found = True
                self.installer.run()

        if not setup_py_in_found:
            self.installer.install_from_rpm_py_rpm()


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
        """RPM Python binding's version info."""
        version_str = self.version
        return Utils.version_str2tuple(version_str)

    @property
    def is_release(self):
        """Release version or not."""
        # version string: N.N.N.N is for release.
        return True if re.match(r'^[\d.]+$', self.version) else False

    @property
    def git_branch(self):
        """Git branch name."""
        info = self.info
        return 'rpm-{major}.{minor}.x'.format(
            major=info[0], minor=info[1])


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
        # Support Python 2.6. subprocess.check_output is new in Python 2.7.
        {
            'src': r'\n    pcout = subprocess\.check_output\(cmd.split\(\)\)\.decode\(\) *?\n', # NOQA
            'dest': '''
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    pcout, _ = p.communicate()
    pcout = pcout.decode()
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

    def exists_in_path(self):
        """Return if setup.py.in exists.

        If RPM version >= 4.10.0-beta1, setup.py.in exist.
        otherwise RPM version <= 4.9.x, setup.py.in does not exist.
        """
        return os.path.isfile(self.IN_PATH)

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

    # rpm.org
    RPM_ORG_BASE_URL = 'http://ftp.rpm.org/releases'
    RPM_ORG_ARCHIVE_URL_FORMAT = (
        RPM_ORG_BASE_URL + '/{branch_name}/rpm-{version}.tar.gz'
    )
    RPM_ORG_ARCHIVE_TOP_DIR_NAME_FORMAT = 'rpm-{version}'
    # github
    RPM_GIT_HUB_BASE_URL = 'https://github.com/rpm-software-management/rpm'
    RPM_GIT_HUB_REPO_URL = '{0}.git'.format(RPM_GIT_HUB_BASE_URL)
    RPM_GIT_HUB_ARCHIVE_URL_FORMAT = (
        RPM_GIT_HUB_BASE_URL + '/archive/{tag_name}.tar.gz'
    )
    RPM_GIT_HUB_ARCHIVE_TOP_DIR_NAME_FORMAT = 'rpm-{tag_name}'

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

    def _download_and_expand_from_archive_url(self):
        archive_dicts = self._get_candidate_archive_dicts()
        max_num = len(archive_dicts)
        found_index = None
        for index, archive_dict in enumerate(archive_dicts):
            url = archive_dict['url']
            Log.info("Downloading archive. '{0}'.".format(url))
            try:
                Cmd.curl_remote_name(url)
            except ArchiveNotFoundError as e:
                Log.info('Archive not found. URL: {0}'.format(url))
                if index + 1 < max_num:
                    Log.info('Try to download next candidate URL.')
                else:
                    raise e
            else:
                found_index = index
                break

        found_archive_dict = archive_dicts[found_index]
        archive_file_name = os.path.basename(found_archive_dict['url'])
        Cmd.tar_extract(archive_file_name)

        return found_archive_dict['top_dir_name']

    def _get_candidate_archive_dicts(self):
        archive_dicts = []

        if self.rpm_py_version.is_release:
            url = self._get_rpm_org_archive_url()
            top_dir_name = self._get_rpm_org_archive_top_dir_name()
            archive_dicts.append({
                'site': 'rpm.org',
                'url': url,
                'top_dir_name': top_dir_name,
            })

        tag_names = self._predict_candidate_git_tag_names()
        for tag_name in tag_names:
            url = self._get_git_hub_archive_url(tag_name)
            top_dir_name = self._get_git_hub_archive_top_dir_name(tag_name)
            archive_dicts.append({
                'site': 'github',
                'url': url,
                'top_dir_name': top_dir_name,
            })

        return archive_dicts

    def _get_rpm_org_archive_url(self):
        url = self.RPM_ORG_ARCHIVE_URL_FORMAT.format(
            branch_name=self.rpm_py_version.git_branch,
            version=self.rpm_py_version.version,
        )
        return url

    def _get_rpm_org_archive_top_dir_name(self):
        top_dir_name = self.RPM_ORG_ARCHIVE_TOP_DIR_NAME_FORMAT.format(
            version=self.rpm_py_version.version
        )
        return top_dir_name

    def _get_git_hub_archive_url(self, tag_name):
        url = self.RPM_GIT_HUB_ARCHIVE_URL_FORMAT.format(
            tag_name=tag_name
        )
        return url

    def _get_git_hub_archive_top_dir_name(self, tag_name):
        top_dir_name = self.RPM_GIT_HUB_ARCHIVE_TOP_DIR_NAME_FORMAT.format(
            tag_name=tag_name
        )
        return top_dir_name

    def _download_and_expand_by_git(self):
        self._do_git_clone()
        return 'rpm'

    def _predict_candidate_git_tag_names(self):
        version = self.rpm_py_version.version
        name_release = 'rpm-{0}-release'.format(version)
        name_non_release = 'rpm-{0}'.format(version)
        tag_names = None
        if self.rpm_py_version.is_release:
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
            repo_url=self.RPM_GIT_HUB_REPO_URL,
        )
        Log.info("Downloading source by git clone. 'branch: {0}'".format(
                 branch))
        _, stderr = Cmd.sh_e(git_clone_cmd)
        # Verify stderr message in addition.
        # Old git (at least v1.7.1) does not return non zero exist status,
        # when running "git clone -b branch" and the branch is not found.
        # https://github.com/git/git/tree/master/Documentation/RelNotes
        if re.match(r'warning: Remote branch [^ ]+ not found', stderr,
                    re.MULTILINE):
            message_format = (
                'fatal: Remote branch {0} not '
                'found in upstream origin.'
            )
            raise InstallError(message_format.format(branch))

    def _predict_git_branch(self):
        git_branch = None

        version_info = self.rpm_py_version.info
        stable_branch = 'rpm-{major}.{minor}.x'.format(
            major=version_info[0],
            minor=version_info[1],
        )
        git_ls_remote_cmd = 'git ls-remote --heads {repo_url} {branch}'.format(
            repo_url=self.RPM_GIT_HUB_REPO_URL,
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

    def install_from_rpm_py_rpm(self):
        """Run install main logic.

        It is run when RPM does not have setup.py.in in the source
        such as the RPM source is old.
        """
        self.rpm.download_and_extract('rpm-python')

        # Find ./usr/lib64/pythonN.N/site-packages/rpm directory.
        downloaded_rpm_dirs = glob.glob('usr/*/*/site-packages/rpm')
        if not downloaded_rpm_dirs:
            raise InstallError('site-packages/rpm directory not found.')
        src_rpm_dir = downloaded_rpm_dirs[0]

        dst_rpm_dir = self.python.python_lib_rpm_dir
        if os.path.isdir(dst_rpm_dir):
            Log.debug("Remove existed rpm directory {0}".format(dst_rpm_dir))
            shutil.rmtree(dst_rpm_dir)
        Log.debug("Copy directory from '{0}' to '{1}'".format(
                  src_rpm_dir, dst_rpm_dir))
        shutil.copytree(src_rpm_dir, dst_rpm_dir)

    def _is_rpm_build_libs_installed(self):
        return self.rpm.is_package_installed('rpm-build-libs')

    def _is_rpm_devel_installed(self):
        return self.rpm.is_package_installed('rpm-devel')

    def _is_popt_devel_installed(self):
        return self.rpm.is_package_installed('popt-devel')

    def _prepare_so_files(self):
        so_file_dict = {
            'rpmio': {
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'rpmio/.libs',
                'require': True,
            },
            'rpm': {
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'lib/.libs',
                'require': True,
            },
            'rpmbuild': {
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'build/.libs',
                'require': True,
            },
            'rpmsign': {
                'sym_src_dir': self.rpm.lib_dir,
                'sym_dst_dir': 'sign/.libs',
            },
        }

        if not self.rpm.has_sys_rpm_rpm_bulid_libs():
            # All the needed so files are installed.
            pass
        elif self.rpm.is_downloadable():
            if not self._is_rpm_build_libs_installed():
                self.rpm.download_and_extract('rpm-build-libs')

                # rpm-sign-libs was splitted from rpm-build-libs
                # from rpm-4.14.1-8 on Fedora.
                try:
                    self.rpm.download_and_extract('rpm-sign-libs')
                except InstallError:
                    pass

                current_dir = os.getcwd()
                work_lib_dir = current_dir + self.rpm.lib_dir
                so_file_dict['rpmbuild']['sym_src_dir'] = work_lib_dir
                so_file_dict['rpmsign']['sym_src_dir'] = work_lib_dir
        elif not self._is_rpm_build_libs_installed():
            message = '''
Required RPM not installed: [rpm-build-libs],
when a RPM download plugin not installed.
'''
            raise InstallError(message)

        for name in so_file_dict:
            so_dict = so_file_dict[name]
            pattern = 'lib{0}.so*'.format(name)
            so_files = Cmd.find(so_dict['sym_src_dir'], pattern)
            if not so_files:
                is_required = so_dict.get('require', False)
                if not is_required:
                    message_format = (
                        "Skip creating symbolic link of "
                        "not existed so file '{0}'"
                    )
                    Log.debug(message_format.format(name))
                    continue

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
                                                    name)
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
                if not os.path.isdir(header_dir):
                    Log.debug("Skip not existed header directory '{0}'".format(
                              header_dir))
                    continue
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
                popt_lib_dirs = [
                    self.rpm.lib_dir,
                    # /lib64/libpopt.so* installed at popt-1.13-7.el6.x86_64.
                    '/lib64',
                ]
                pattern = 'libpopt.so*'
                popt_so_file = None
                for popt_lib_dir in popt_lib_dirs:
                    so_files = Cmd.find(popt_lib_dir, pattern)
                    if so_files:
                        popt_so_file = so_files[0]
                        break

                if not popt_so_file:
                    message = 'so file pattern {0} not found at {1}'.format(
                        pattern, str(popt_lib_dirs)
                    )
                    raise InstallError(message)

                cmd = 'ln -sf {0} ../lib/.libs/libpopt.so'.format(
                      popt_so_file)
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

    @property
    def python_lib_dir(self):
        """site-packages directory such as /../pythonN.N/site-packages ."""
        return get_python_lib()

    @property
    def python_lib_rpm_dir(self):
        """Installed directory of RPM Python binding."""
        return os.path.join(self.python_lib_dir, 'rpm')

    def is_python_binding_installed(self):
        """Check if the Python binding module has already installed.

        Consider below cases.
        - pip command is not installed.
        - The installed RPM Python binding does not have information
          showed as a result of pip list.
        """
        is_installed = False
        is_install_error = False

        try:
            is_installed = self.is_python_binding_installed_on_pip()
        except InstallError:
            # Consider a case of pip is not installed in old Python (<= 2.6).
            is_install_error = True
        if not is_installed or is_install_error:
            init_py = os.path.join(self.python_lib_rpm_dir, '__init__.py')
            if os.path.isfile(init_py):
                is_installed = True

        return is_installed

    def is_python_binding_installed_on_pip(self):
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

    def _get_pip_cmd(self):
        pip_cmd = None
        # pip is already installed in Python 2 >=2.7.9 or Python 3 >=3.4 .
        # https://pip.pypa.io/en/stable/installing/#installation
        if ((sys.version_info >= (2, 7, 9) and sys.version_info < (2, 8))
           or sys.version_info >= (3, 4)):
            pip_cmd = '{0} -m pip'.format(self.python_path)
        else:
            # pip can be installed by get-pip.py.
            pip_cmd = 'pip'
        return pip_cmd

    def _get_pip_version(self):
        cmd = '{0} --version'.format(self._get_pip_cmd())
        pip_version_out = Cmd.sh_e_out(cmd)
        pip_version = pip_version_out.split()[1]
        return pip_version

    def _get_pip_list_json_obj(self):
        cmd = '{0} list --format json'.format(self._get_pip_cmd())
        json_str = Cmd.sh_e_out(cmd)
        json_obj = json.loads(json_str)
        return json_obj

    def _get_pip_list_lines(self):
        cmd = '{0} list'.format(self._get_pip_cmd())
        out = Cmd.sh_e_out(cmd)
        lines = out.split('\n')
        return lines


class Rpm(object):
    """A class for RPM environment including DNF and Yum."""

    def __init__(self, rpm_path, **kwargs):
        """Initialize this class."""
        is_dnf = True if Cmd.which('dnf') else False

        is_file_checked = kwargs.get('check', True)
        if is_file_checked and not os.path.isfile(rpm_path):
            raise InstallError("RPM binary command '{0}' not found.".format(
                               rpm_path))
        self.rpm_path = rpm_path
        self.is_dnf = is_dnf
        self.arch = Cmd.sh_e_out('uname -m').rstrip()
        self._lib_dir = None

    @property
    def version(self):
        """RPM vesion string."""
        stdout = Cmd.sh_e_out('{0} --version'.format(self.rpm_path))
        rpm_version = stdout.split()[2]
        return rpm_version

    @property
    def version_info(self):
        """RPM version info."""
        version_str = self.version
        return Utils.version_str2tuple(version_str)

    def is_system_rpm(self):
        """Check if the RPM is system RPM."""
        sys_rpm_paths = [
            '/usr/bin/rpm',
            # On CentOS6, system RPM is installed in this directory.
            '/bin/rpm',
        ]
        matched = False
        for sys_rpm_path in sys_rpm_paths:
            if self.rpm_path.startswith(sys_rpm_path):
                matched = True
                break
        return matched

    def has_sys_rpm_rpm_bulid_libs(self):
        """Return if the sysmtem RPM has rpm-build-libs pacakage.

        rpm-bulid-libs was created from rpm 4.9.0-0.beta1.1 on Fedora.
        https://src.fedoraproject.org/rpms/rpm/blob/master/f/rpm.spec
        > * 4.9.0-0.beta1.1
        > - split librpmbuild and librpmsign to a separate rpm-build-libs
        >   package
        """
        return self.version_info >= (4, 9, 0)

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
            message_format = (
                'CMD Return Code: [{0}], Stdout: [{1}], Stderr: [{2}]'
            )
            Log.debug(message_format.format(returncode, stdout, stderr))
            if returncode != 0:
                message = 'CMD: [{0}], Return Code: [{1}] at [{2}]'.format(
                    cmd, returncode, os.getcwd())
                if stderr is not None:
                    message += ' Stderr: [{0}]'.format(stderr)
                raise InstallError(message)

            if stdout is not None:
                stdout = stdout.decode('utf-8')
            if stderr is not None:
                stderr = stderr.decode('utf-8')

            return (stdout, stderr)
        except Exception as e:
            try:
                proc.kill()
            except Exception:
                pass
            raise e

    @classmethod
    def sh_e_out(cls, cmd, **kwargs):
        """Run the command. and returns the stdout."""
        cmd_kwargs = {
            'stdout': subprocess.PIPE,
        }
        cmd_kwargs.update(kwargs)
        return cls.sh_e(cmd, **cmd_kwargs)[0]

    @classmethod
    def cd(cls, directory):
        """Change directory. It behaves like "cd directory"."""
        Log.debug('CMD: cd {0}'.format(directory))
        os.chdir(directory)

    @classmethod
    @contextlib.contextmanager
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
    def tar_extract(cls, tar_comp_file_path):
        """Extract tar.gz or tar bz2 file.

        It behaves like
          - tar xzf tar_gz_file_path
          - tar xjf tar_bz2_file_path
        It raises tarfile.ReadError if the file is broken.
        """
        try:
            with contextlib.closing(tarfile.open(tar_comp_file_path)) as tar:
                tar.extractall()
        except tarfile.ReadError as e:
            message_format = (
                'Extract failed: '
                'tar_comp_file_path: {0}, reason: {1}'
            )
            raise InstallError(message_format.format(tar_comp_file_path, e))

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


class Utils(object):
    """A general utility class."""

    @classmethod
    def version_str2tuple(cls, version_str):
        """Version info.

        tuple object. ex. ('4', '14', '0', 'rc1')
        """
        version_info_list = re.findall(r'[0-9a-zA-Z]+', version_str)

        def convert_to_int(string):
            value = None
            if re.match(r'^\d+$', string):
                value = int(string)
            else:
                value = string
            return value

        version_info_list = [convert_to_int(s) for s in version_info_list]

        return tuple(version_info_list)


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
