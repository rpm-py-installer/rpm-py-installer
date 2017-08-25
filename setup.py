import os
import sys

import setuptools
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

from rpm_py_installer.version import VERSION


def install_rpm_py():
    if sys.platform in ['darwin', 'linux']:
        python_path = sys.executable
        cmd = 'PYTHON="{0}" ./install'.format(python_path)
        exit_status = os.system(cmd)
        if exit_status != 0:
            raise Exception('Command failed: {0}'.format(cmd))


class InstallCommand(install):
    """A class for "pip install".

    Handled by "pip install rpm-py-installer",
    when the package should be published as a source distribution (sdist).

    If pip's cache for rpm-py-installer is available, it is not handled.
    In the case, install as follows.

    $ rm -rf ~/.cache/pip
    $ pip install rpm-py-installer

    or

    $ pip install --no-cache-dir rpm-py-installer

    See https://pip.pypa.io/en/stable/reference/pip_install/#caching .
    """
    def run(self):
        install.run(self)
        install_rpm_py()


class DevelopCommand(develop):
    """A class for setuptools development mode.

    Handled by "pip install -e".
    """
    def run(self):
        develop.run(self)
        install_rpm_py()


class EggInfoCommand(egg_info):
    """A class for egg-info.

    Handled by "pip install .".
    """
    def run(self):
        egg_info.run(self)
        install_rpm_py()


setuptools.setup(
    name='rpm-py-installer',
    version=VERSION,
    license='MIT',
    description='RPM Pythoon Installer',
    long_description='A installer for RPM Python binding module.',
    author='Jun Aruga',
    author_email='jaruga@redhat.com',
    url='https://github.com/junaruga/rpm-py-installer',
    packages=[
        'rpm_py_installer',
    ],
    install_requires=[],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Installation/Setup',
    ],
    scripts=[
        'install',
    ],
    cmdclass={
      'install': InstallCommand,
      'develop': DevelopCommand,
      'egg_info': EggInfoCommand,
    },
)
