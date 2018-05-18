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

| NAME | Description | Value | Default |
| ---- | ----------- | ----- | ------- |
| RPM_PY_RPM_BIN | Path to rpm | /path/to/rpm | rpm |
| RPM_PY_VERSION | Installed python module's version | N.N.N.N |  Same version with rpm |
| RPM_PY_GIT_BRANCH | Branch name for [RPM git repo](https://github.com/rpm-software-management/rpm). If this option is set, `rpm-py-installer` downloads the RPM source by `git clone` rather than downloading the archive file to get the Python binding. | ex. master, rpm-4.14.x | None |
| RPM_PY_OPTM | Use optimized `setup.py` for the Python binding for comfort install? Or Set "false" to use original one. | true/false | true |
| RPM_PY_VERBOSE | Verbose mode? | true/false | false |
| RPM_PY_WORK_DIR_REMOVED | Remove work directory? Set "false" to see used archive. | true/false | true |


## FAQ

- Q1. I got an install error.
- A1. Could you run below command and check outputted log?

  ```
  $ RPM_PY_VERBOSE=true pip install -vvv rpm-py-installer
  ```

  or

  ```
  $ RPM_PY_VERBOSE=true python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```

- Q2. What is the dependency RPM packages for `rpm-py-installer`?
- A2. Following packages are required on Fedora.
  - `rpm-libs`
  - one of dnf download plugin(`dnf-plugins-core`), `yumdownloader` or `rpm-devel`

  If `rpm-devel` has been installed, it is used. If not, the download utiliy is used to download and use the build required RPM packages in installing process.

  To install dnf download plugin on DNF environment such as Fedora.

  ```
  # dnf install 'dnf-command(download)'
  ```

  To install `yumdownloader` on Yum environment such as CentOS.

  ```
  # yum install /usr/bin/yumdownloader
  ```

  See also installed packages in [Dockerfile for testing](../.travis/Dockerfile).


- Q3. Does this installer install the Python binding module on system Python (`/usr/bin/python*`)?
- A3. No. The installer skips installing it on system Python.
  It is recommended that you would install it manually from the RPM package(`python{,2,3}-rpm`).


- Q4. How is `rpm-py-installer` version mapped to `python[23]-rpm` version?
- A4. The version mapping's default behavior is to use same version with the system RPM's version on local. See [#94](https://github.com/junaruga/rpm-py-installer/issues/94) for detail.

- Q5. Is it possible to install the Python binding module's specifying the version.
- A5. Yes. Possible. But it may be failed to install. Set version number seeing [RPM release page](https://github.com/rpm-software-management/rpm/releases).

  ```
  $ RPM_PY_VERSION=4.13.0 python -c "$(curl -fsSL https://raw.githubusercontent.com/junaruga/rpm-py-installer/master/install.py)"
  ```
- Q6. How to update my Python package's RPM spec file `foo.spec`?
- A6. You can add below command in your spec file `foo.spec`.

  ```
  sed -i '/rpm-py-installer/d' setup.py
  ```

  or set `setup.py`'s `install_requires` conditionally. Refer the samples [`setup.py`](/tests/sample/setup.py) or [rebase-helper's `setup.py`](https://github.com/rebase-helper/rebase-helper/blob/master/setup.py). If you have a request for this situation, ask us on [the issue page](https://github.com/junaruga/rpm-py-installer/issues/134)

- Q7. I got message "Failed building wheel for rpm-py-installer" when installing `pip install rpm-py-installer`. Is it problem?
- A7. No, it isn't. `rpm-py-installer` makes own `python setup.py bdist_wheel` raise an error, to always disable `wheel` cache to run own install process.

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
rpm-py-installer 0.4.0
rpm-python       4.13.0.1
```
