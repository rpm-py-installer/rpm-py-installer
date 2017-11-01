# RPM Python binding Installer
[![PyPI](https://img.shields.io/pypi/v/rpm-py-installer.svg)](https://pypi.python.org/pypi/rpm-py-installer)
[![Build Status](https://travis-ci.org/junaruga/rpm-py-installer.svg?branch=master)](https://travis-ci.org/junaruga/rpm-py-installer)

`rpm-py-installer` installs [a RPM Python binding module](https://github.com/rpm-software-management/rpm/tree/master/python) (`rpm-python` or `rpm` for new version) on non-system Python, such as a source compiled Python, a Python on virtualenv and pyenv environment, considering installed RPM itself.

It installs same version's Python binding with the system RPM safely.

## Install the RPM Python binding module by rpm-py-installer

`rpm-py-installer` provides several ways to install.

### Install by pip

```
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

$ pip list
Package          Version-
---------------- --------
pip              9.0.1
rpm-py-installer 0.4.0
rpm-python       4.13.0.1 <= Same version with the system RPM's one.
setuptools       28.8.0

$ python -c "import rpm; print(rpm.__version__)"
4.13.0.1
```

### Install as a required dependency for your pacakge

Add `rpm-py-installer` to your package's `setup.py` `install_requires`.

```
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

```
$ pip install your_package
```

### Direct install

If you want to install the Python binding module without `rpm-py-installer` package.

```
$ /path/to/python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
```

See Users Guide for detail.

## Usage

See [Users Guide](docs/users_guide.md).

## Communities using rpm-py-installer

[rebase-helper](https://github.com/rebase-helper/rebase-helper)

## License

MIT
