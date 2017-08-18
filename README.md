# rpm-python-installer

This script installs RPM Python binding module on any Python,
considering installed RPM's version.

If you want to install `rpm-python` to below python3's virtualenv environment,

```
$ which python3
/usr/local/python-3.6.1/bin/python3
```

```
$ git clone REPO_URL
$ ls rpm-python-installer/installer.sh
```

```
$ cd $PROJECT_DIR

$ virtualenv --python=python3 ./venv

(venv) $ /path/to/rpm-python-installer/installer.sh

(venv) $ pip list | grep rpm
rpm-python        4.13.0.1
```
