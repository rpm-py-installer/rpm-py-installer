# Users Guide

## How to install

```
$ [VAR=VALUE] pip install rpm-py-installer
```
or

```
$ [VAR=VALUE] /path/to/python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
```

## Environment variables

| NAME | Description | Default |
| ---- | ----------- | ------- |
| RPM | Path to rpm | rpm |
| RPM_VERSION | Installed python module's version | Same version with rpm |
| VERBOSE | Verbose mode. true/false | false |


## FAQ

- Q1. I ran `pip install rpm-py-installer` or ran `rpm-py-installer` as a required install dependency in `setup.py`. But the Python binding is not installed.
- A1. This issue is happened if `wheel` package is installed in your Python environment, and the install is after 2nd time, when the cache is used for `rpm-py-installer`. The installing process for the Python binding module is skipped. In this case, run `pip install` with `--no-cache-dir` option.

  ```
  $ pip install --no-cache-dir rpm-py-installer
  ```

  or

  ```
  $ rm -rf ~/.cache/pip

  $ pip install rpm-py-installer
  ```

- Q2. I got an install error.
- A2. Could you run below command and check outputted log?

  ```
  $ VERBOSE=true pip install --no-cache-dir -vvv rpm-py-installer
  ```

  or

  ```
  $ VERBOSE=true python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```

- Q3. What is the dependency RPM packages for `rpm-py-installer`?
- A3. Following packages are required on Fedora.
  - rpm-libs
  - rpm-devel

  See also installed packages in [Dockerfile for testing](../.travis/Dockerfile).


- Q4. Does this installer install the Python binding module on system Python (`/usr/bin/python*`)?
- A4. No. The installer skips installing it on system Python.
  It is recommended that you would install it manually from the RPM package(`python{,2,3}-rpm`).


- Q5. Is it possible to install the Python binding module's specifying the version.
- A5. Yes. Possible. But it may be failed to install. Set version number seeing [RPM release page](https://github.com/rpm-software-management/rpm/releases).

  ```
  $ RPM_VERSION=4.13.0 python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```

## Tutorial

For example, in case of that you want to install the Python binding module on virtualenv environment.

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

Move to a project that you want to install the Python binding module.

```
$ cd $PROJECT_DIR

$ python3 -m venv ./venv

$ source venv/bin/activate
```

```
(venv) $ pip install rpm-py-installer
```

```
(venv) $ pip3 list | grep rpm
rpm-py-installer 0.1.0
rpm-python       4.13.0.1
```
