# Development Guide

## Releasing

Bump version.

```
$ vi rpm_py_installer/version.py
$ git add rpm_py_installer/version.py
$ git commit -m 'Bump version X.Y.Z.'
```

Tagging.

```
$ git tag -a X.Y.Z -m 'Tagging X.Y.Z'
```

Upload source distribution to PyPI.
Run it on virtualenv, because right now install process is run.

```
$ source venv/bin/activate
(venv) $ python3 setup.py sdist upload
(venv) $ deactivate
```

Push the tag information.

```
$ git push origin X.Y.Z
$ git push origin master
```
