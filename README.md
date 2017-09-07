# rpm-py-installer
[![PyPI](https://img.shields.io/pypi/v/rpm-py-installer.svg)](https://pypi.python.org/pypi/rpm-py-installer)
[![Build Status](https://travis-ci.org/junaruga/rpm-py-installer.svg?branch=master)](https://travis-ci.org/junaruga/rpm-py-installer)

`rpm-py-installer` installs [a RPM Python binding module](https://github.com/rpm-software-management/rpm/tree/master/python) (`rpm-python` or `rpm` for new version) on non-system Python, such as a source compiled Python, a Python on virtualenv and pyenv environment, considering installed RPM itself.

## Install the RPM Python binding module by rpm-py-installer

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

See Users Guide FAQ Q1 about a case of required `--no-cache-dir`.

### Install the Python binding module as a required dependency for your pacakge

Add `rpm-py-installer` to your package's `setup.py` `install_requires`.
Then run `pip install`.

```
$ pip install --no-cache-dir your_package
```

See Users Guide FAQ Q1 about a case of required `--no-cache-dir`.

### Direct install

If you want to install the Python binding module without `rpm-py-installer` package.

See Users Guide for detail.

```
$ /path/to/python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
```

### Usage

See [Users Guide](docs/users_guide.md).

## License

MIT
