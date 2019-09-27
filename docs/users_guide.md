# User's Guide

## How to install

``` ShellSession
$ [VAR=VALUE] pip install rpm-py-installer
```
or

``` ShellSession
$ [VAR=VALUE] /path/to/python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
```

## Environment variables

| NAME | Description | Value | Default |
| ---- | ----------- | ----- | ------- |
| RPM_PY_INSTALL_BIN | Install RPM Python binding from binary package? | true/false | false |
| RPM_PY_SYS | Install the Python binding using the system Python? | true/false | false |
| RPM_PY_RPM_BIN | Path to rpm | /path/to/rpm | rpm |
| RPM_PY_VERSION | Installed python module's version | N.N.N.N |  Same version as rpm |
| RPM_PY_GIT_BRANCH | Branch name for the [RPM git repo](https://github.com/rpm-software-management/rpm). If this option is set, then `rpm-py-installer` downloads the RPM sources via `git clone` rather than downloading the archive file to get the Python binding. | ex. master, rpm-4.14.x | None |
| RPM_PY_OPTM | Use optimized `setup.py` for the Python binding for comfortable installation? Or Set "false" to use the original one. | true/false | true |
| RPM_PY_VERBOSE | Verbose mode? | true/false | false |
| RPM_PY_WORK_DIR_REMOVED | Remove work directory afterwards? Set "false" to preserve the archive used during the installation. | true/false | true |


## FAQ

- Q1. I got an install error.
- A1. Could you run following command and check output?

  ``` ShellSession
  $ RPM_PY_VERBOSE=true pip install -vvv rpm-py-installer
  ```

  or

  ``` ShellSession
  $ RPM_PY_VERBOSE=true python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```

- Q2. What are the RPM dependencies for `rpm-py-installer`?
- A2. Following packages are required on Fedora:
  - `rpm-libs`
  - `gcc`
  - one of the following: dnf download plugin(`dnf-plugins-core`), `yumdownloader` or `rpm-devel`

  If `rpm-devel` has been installed, then it is used. If not, the download utility is used to download and use the required RPM packages for the build in install process.

  To install dnf download plugin in a DNF environment such as Fedora:
  ``` ShellSession
  # dnf install 'dnf-command(download)'
  ```

  To install `yumdownloader` in a Yum environment such as CentOS:
  ``` ShellSession
  # yum install /usr/bin/yumdownloader
  ```

  See also the installed packages in [Dockerfiles for testing](../ci/).


- Q3. Does this installer install the Python binding for the system Python (`/usr/bin/python*`)?
- A3. No. The installer skips installing it for the system Python.
  It is recommended that you would install it the python binding using the the RPM package(`python{,2,3}-rpm`) instead for a system wide installation.


- Q4. How is `rpm-py-installer` version mapped to `python[23]-rpm` version?
- A4. The version mapping's default behavior is to use same version as the system RPM's version. See [#94](https://github.com/junaruga/rpm-py-installer/issues/94) for details.

- Q5. Is it possible to install the Python binding of a specific version?
- A5. Yes, it is possible, but it may fail to install. Set the version number (see the [RPM release page](https://github.com/rpm-software-management/rpm/releases) for valid choices) using the environment variable `RPM_PY_VERSION`.

  ``` ShellSession
  $ RPM_PY_VERSION=4.13.0 python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```

- Q6. How to update my Python package's RPM spec file `foo.spec`?
- A6. You can add the following command to your spec file `foo.spec`:

  ``` bash
  sed -i '/rpm-py-installer/d' setup.py
  ```

  or set `setup.py`'s `install_requires` conditionally. Refer to the sample [`setup.py`](/tests/sample/setup.py) or [rebase-helper's `setup.py`](https://github.com/rebase-helper/rebase-helper/blob/master/setup.py). If you have a request for this situation, ask us on [the issue page](https://github.com/junaruga/rpm-py-installer/issues/134).

- Q7. I got message "Failed building wheel for rpm-py-installer" when installing `pip install rpm-py-installer`. Is that a problem?
- A7. No, it isn't. `rpm-py-installer`'s own `python setup.py bdist_wheel` raises an error, so always disable `wheel` cache to run your own install process.

## Tutorial

To install the Python binding inside a virtualenv environment, proceed as follows:

``` ShellSession
$ which rpm
/usr/bin/rpm

$ rpm --version
RPM version 4.13.0.1
```

``` ShellSession
$ which python3
/usr/local/python-3.6.1/bin/python3

$ python3 --version
Python 3.6.1
```

Move to a project that you want to install the Python binding for:

``` ShellSession
$ cd $PROJECT_DIR

$ python3 -m venv ./venv

$ source venv/bin/activate
```

``` ShellSession
(venv) $ pip install rpm-py-installer
```

``` ShellSession
(venv) $ pip3 list | grep rpm
rpm-py-installer 0.4.0
rpm-python       4.13.0.1
```
