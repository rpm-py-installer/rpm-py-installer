# RPM Python binding Installer
[![PyPI](https://img.shields.io/pypi/v/rpm-py-installer.svg)](https://pypi.python.org/pypi/rpm-py-installer)
[![GitHub Actions Build Status](https://github.com/junaruga/rpm-py-installer/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/junaruga/rpm-py-installer/actions/workflows/build-and-test.yml)

`rpm-py-installer` is to enable [the RPM Python binding](https://github.com/rpm-software-management/rpm/tree/master/python) in any Python environment. The environment can be a non-system Python, a source compiled Python, a Python in a virtualenv, pyenv environment, etc. It installs the Python binding matching the version of the system RPM in a safe manner. The reason for the project's existence is that [the RPM project is not positive to upload the Python binding to PyPI](https://github.com/rpm-software-management/rpm/issues/273), and [the "rpm" name is reserved in PyPI](https://pypi.org/project/rpm).

## Getting started

`rpm-py-installer` provides several ways to install the RPM Python binding.

### Install via pip

``` ShellSession
$ rpm --version
RPM version 4.13.0.1

$ which python
/path/to/python

$ which pip
/path/to/pip_on_the_python

$ pip list
Package    Version
---------- -------
pip        9.0.1
setuptools 28.8.0

$ pip install rpm-py-installer
```

`rpm-python` or the `rpm` package for the new version is installed via the `rpm-py-installer` package.

``` ShellSession
$ pip list
Package          Version
---------------- --------
pip              9.0.1
rpm-py-installer 0.4.0
rpm-python       4.13.0.1 <= Same version with the system RPM's one.
setuptools       28.8.0

$ python -c "import rpm; print(rpm.__version__)"
4.13.0.1
```

### Install as a required dependency of your package

Add `rpm-py-installer` to your package's `setup.py` `install_requires`.

``` ShellSession
$ pwd
/path/to/your_project

$ vi setup.py
...
setup(
...
    install_requires=[
...
        # This installs the rpm package.
        'rpm-py-installer',
...
    ],
...
)
...
```

Upload your package to PyPI.
And run `pip install`.

``` ShellSession
$ pip install your_package
```

Note that if you would provide your project as a RPM package, please consider to apply a conditional import to your `setup.py` not to provide `rpm-py-installer` in the environment. Refer to [the setup.py sample](/tests/sample/setup.py) and the User's Guide FAQ Q6.


### Install the rpm Python binding directly

If you want to install the Python binding without explicitly installing the `rpm-py-installer` package, proceed as follows:

``` ShellSession
$ pip list
Package    Version
---------- -------
pip        9.0.1
setuptools 28.8.0

$ python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"

$ pip list
Package          Version
---------------- --------
pip              9.0.1
rpm-python       4.13.0.1 <= Same version with the system RPM's one.
setuptools       28.8.0
```

## Usage

See [User's guide](docs/users_guide.md).

## Contributing

We encourage you to contribute to `rpm-py-installer`! Please check out the [Contributing guide](CONTRIBUTING.md) for guidelines how to proceed. See the [Developer's guide](docs/developers_guide.md) for further details.

## Supported environments

`.travis.yml` shows the currently supported environments.

* Fedora
* CentOS (>= 6)
* Ubuntu (>= trusty)
* openSUSE Leap (>= 15.0) and Tumbleweed

The following environments are currently unsupported. To be supported, we need to add tests to the CI.

* Mac OSX (ticket [#155](https://github.com/junaruga/rpm-py-installer/issues/155))

## Communities using rpm-py-installer

[rebase-helper](https://github.com/rebase-helper/rebase-helper), [koji](https://pagure.io/koji), [rpkg](https://pagure.io/rpkg)

## License

MIT
