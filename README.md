# rpm-py-installer

This tool installs RPM Python binding module (`rpm-python` or `rpm` (new version)) on any Python, considering installed system RPM's version.

## How to install

### Synopsis

```
$ [PYTHON=path/to/python] bash -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install)"
```

### Environment variables

| NAME | Description | Default |
| ---- | ----------- | ------- |
| PYTHON | Path to python | python3 |
| RPM | Path to rpm | rpm |
| RPM_VERSION | Installed python module's version | Same version with rpm |


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

## Note

- If you want to install the module on `/usr/bin/python{3,2,}`, install it from the RPM package(`python{3,2}-rpm`).
