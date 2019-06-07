# RPM Python binding Installer
[![PyPI](https://img.shields.io/pypi/v/rpm-py-installer.svg)](https://pypi.python.org/pypi/rpm-py-installer)
[![Travis Build Status](https://travis-ci.org/junaruga/rpm-py-installer.svg?branch=master)](https://travis-ci.org/junaruga/rpm-py-installer)
[![Shippable Build Status](https://api.shippable.com/projects/5bb13c0997da11060049f4ad/badge?branch=master)](https://app.shippable.com/github/junaruga/rpm-py-installer/runs?branchName=master)

`rpm-py-installer` is to enable [the RPM Python binding](https://github.com/rpm-software-management/rpm/tree/master/python) in any Python environment.

The environment is non-system Python, a source compiled Python, a Python on virtualenv, pyenv environment and etc.

It installs same version's Python binding with the system RPM safely.

## Install the RPM Python binding by rpm-py-installer

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
```

`rpm-python` or `rpm` package for new version is installed with `rpm-py-installer` package.

```
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

Note that if you would provide your project as a RPM package, please consider to apply a conditional import to your `setup.py` not to provide `rpm-py-installer` in the environment. Refer [the setup.py sample](/tests/sample/setup.py) and Users Guide FAQ Q6.


### Install directly without rpm-py-installer package

If you want to install the Python binding without `rpm-py-installer` package.

```
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

See [Users Guide](docs/users_guide.md).

## Communities using rpm-py-installer

[rebase-helper](https://github.com/rebase-helper/rebase-helper), [koji](https://pagure.io/koji), [rpkg](https://pagure.io/rpkg)

## License

MIT
