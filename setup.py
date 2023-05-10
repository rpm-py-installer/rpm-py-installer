"""Classes to set up and install rpm-py-installer."""
import subprocess
import sys
from distutils.cmd import Command

import setuptools
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info
from setuptools.command.install import install

from rpm_py_installer.version import VERSION


def run_cmd(cmd):
    """Run a command."""
    exit_status = 0
    message = ''

    proc = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    proc.wait()
    exit_status = proc.returncode
    stdout = proc.stdout.read().decode()
    stderr = proc.stderr.read().decode()
    message = '''
Command: {0}
Return Code: [{1}]
Stdout: [{2}]
Stderr: [{3}]
'''.format(cmd, exit_status, stdout, stderr)

    return (exit_status, message)


def install_rpm_py():
    """Install RPM Python binding."""
    python_path = sys.executable
    cmd = '{0} install.py'.format(python_path)
    exit_status, message = run_cmd(cmd)

    if exit_status != 0:
        raise Exception(message)


class InstallCommand(install):
    """A class for "pip install".

    Handled by "pip install rpm-py-installer",
    when the package is published to PyPI as a source distribution (sdist).
    """

    def run(self):
        """Run install process."""
        install.run(self)
        install_rpm_py()


class DevelopCommand(develop):
    """A class for setuptools development mode.

    Handled by "pip install -e".
    """

    def run(self):
        """Run install process with development mode."""
        develop.run(self)
        install_rpm_py()


class EggInfoCommand(egg_info):
    """A class for egg-info.

    Handled by "pip install .".
    """

    def run(self):
        """Run egg_info process."""
        egg_info.run(self)
        install_rpm_py()


class BdistWheelCommand(Command):
    """A class for "pip bdist_wheel".

    Raise exception to always disable wheel cache.

    See https://github.com/pypa/pip/issues/4720
    """

    user_options = [
        ("dist-dir=", "d", "For compatibility. Ignored."),
    ]

    def initialize_options(self):
        """Initilize options.

        Just extend the super class's abstract method.
        """
        self.dist_dir = None

    def finalize_options(self):
        """Finalize options.

        Just extend the super class's abstract method.
        """
        pass

    def run(self):
        """Run bdist_wheel process.

        It raises error to make the method fail intentionally.
        """
        raise Exception('bdist_wheel is not supported')


setuptools.setup(
    name='rpm-py-installer',
    version=VERSION,
    license='MIT',
    description='RPM Python binding Installer',
    long_description='''
An installer to enable the RPM Python binding in any environment.
See "Homepage" on GitHub for detail.
''',
    author='Jun Aruga',
    author_email='jaruga@redhat.com',
    maintainer='Nikola Forró',
    maintainer_email='nforro@redhat.com',
    url='https://github.com/rpm-py-installer/rpm-py-installer',
    packages=[
        'rpm_py_installer',
    ],
    # Keep install_requires empty to run install.py directly.
    install_requires=[],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'System :: POSIX :: Linux',
        'Topic :: System :: Installation/Setup',
    ],
    scripts=[
        'install.py',
    ],
    cmdclass={
      'install': InstallCommand,
      'develop': DevelopCommand,
      'egg_info': EggInfoCommand,
      'bdist_wheel': BdistWheelCommand,
    },
)
