# rpm-py-installer
[![PyPI](https://img.shields.io/pypi/v/rpm-py-installer.svg)](https://pypi.python.org/pypi/rpm-py-installer)
[![Build Status](https://travis-ci.org/junaruga/rpm-py-installer.svg?branch=master)](https://travis-ci.org/junaruga/rpm-py-installer)

`rpm-py-installer` installs [a RPM Python binding module](https://github.com/rpm-software-management/rpm/tree/master/python) (`rpm-python` or `rpm` for new version) on non-system Python such as a source compiled Python, a Python on virtualenv, and  a Python on pyenv environment, considering installed RPM itself.

## Install a RPM Python binding module by rpm-py-installer

`rpm-py-installer` provides several ways to install.

### Install by pip

```
$ rpm --version
RPM version 4.13.0.1

$ which python
/path/to/your_python

$ which pip
/path/to/pip_on_your_python

$ pip list
Package    Version
---------- -------
pip        9.0.1
setuptools 28.8.0

$ pip install --no-cache-dir rpm-py-installer

$ pip list
Package          Version-
---------------- --------
pip              9.0.1
rpm-py-installer 0.1.0
rpm-python       4.13.0.1
setuptools       28.8.0
```

### Install as install dependency for your Python module.

Add `rpm-py-installer` in `setup.py` `install_requires` to install the RPM Python binding module.

### Direct install

If you want to install the Python binding module with `rpm-py-installer` package.

You can set environment variables as options. See Users Guide for detail.

```
$ [VAR=VALUE] bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install)"
```

### Usage

See [Users Guide](docs/users_guide.md).

## License

MIT
