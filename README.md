# rpm-python-installer

This script installs RPM Python binding module on any Python,
considering installed system RPM's version.

## How to install

For example.
In case of that you want to install system RPM version's python binding module
to below python3's virtualenv environment.

```
$ which rpm
/usr/bin/rpm

$ rpm --version
RPM version 4.13.0.1
```

```
$ which python3
/usr/local/python-3.6.1/bin/python3

$ python3 --version
Python 3.6.1
```

### Case 1: Install on virtualenv

Move to a project that you want to install the python binding module.

```
$ cd $PROJECT_DIR

$ virtualenv --python=python3 ./venv
```

```
(venv) $ bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/py-rpm-installer/master/install)"
```

```
(venv) $ pip3 list | grep rpm
rpm-python        4.13.0.1
```

### Case 2: Install on specified Python.


```
$ sudo PYTHON=/usr/local/python-3.6.1/bin/python3 \
    bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/py-rpm-installer/master/install)"
```

```
$ /usr/local/python-3.6.1/bin/pip3 list | grep rpm
rpm-python            4.13.0.1
```
