# Users Guide

## How to install

```
$ pip install rpm-py-installer
```
or

```
$ [VAR=VALUE] bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install)"
```

## Environment variables

| NAME | Description | Default |
| ---- | ----------- | ------- |
| PYTHON | Path to python | python3 |
| RPM | Path to rpm | rpm |
| RPM_VERSION | Installed python module's version | Same version with rpm |
| VERBOSE | Verbose mode. true/false | false |


## Note

- If pip's cache for rpm-py-installer is available and used, installing process was skipped. Remove pip's cache directory or run `pip install` with `--no-cache-dir` option.

  ```
  $ rm -rf ~/.cache/pip
  $ pip install rpm-py-installer
  ```

  or

  ```
  $ pip install --no-cache-dir rpm-py-installer
  ```

- following package are required on Fedora.
  - rpm-libs
  - rpm-devel

  See installed packages in [Dockerfile for testing](../tests/docker/Dockerfile) for detail.

- If you want to install the Python binding module on system Python (`/usr/bin/python{3,2,})`, install it manually from the RPM package(`python{,2,3}-rpm`).

## Tutorial

For example.
In case of that you want to install the Python binding module for below RPM
to below python3 environment.

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

### Case 1: Install the python module on virtualenv

Move to a project that you want to install the python binding module.

```
$ cd $PROJECT_DIR

$ virtualenv --python=python3 ./venv

$ source venv/bin/activate
```

```
(venv) $ bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install)"
```

```
(venv) $ pip3 list | grep rpm
rpm-python        4.13.0.1
```

### Case 2: Install the module on source compiled Python.

```
$ sudo PYTHON=/usr/local/python-3.6.1/bin/python3 \
    bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install)"
```

```
$ /usr/local/python-3.6.1/bin/pip3 list | grep rpm
rpm-python            4.13.0.1
```
