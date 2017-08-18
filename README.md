# rpm-python-installer

This script installs RPM Python binding module on any Python,
considering installed RPM's version.

## How to install

If you want to install the module `rpm-python`
to below python3's virtualenv environment,

```
$ which python3
/usr/local/python-3.6.1/bin/python3
```

```
$ which rpm
/usr/bin/rpm

$ rpm --version
RPM version 4.13.0.1
```

```
$ git clone REPO_URL
$ ls rpm-python-installer/installer.sh
```

Move to a project that you want to install the python binding module.

```
$ cd $PROJECT_DIR

$ virtualenv --python=python3 ./venv

(venv) $ /path/to/rpm-python-installer/installer.sh

(venv) $ pip list | grep rpm
rpm-python        4.13.0.1

(venv) $ python -c 'import rpm; print(rpm.__version__)'
4.13.0.1
```
