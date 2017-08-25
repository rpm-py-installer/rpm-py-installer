# Development Guide

## Releasing

Bump version `X.Y.Z`.

```
$ vi rpm_py_installer/version.py
```

Do `git add`, `git commit` and tagging.

```
$ python3 scripts/release.py
```

Upload source distribution to PyPI.
Run it on virtualenv, because right now install process is run.

```
$ source venv/bin/activate
(venv) $ python3 setup.py sdist upload
(venv) $ deactivate
```

Push the commit and tag information to remote repository.

```
$ git push origin master
$ git push origin vX.Y.Z
```
