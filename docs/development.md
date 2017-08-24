# Development Guide

## Releasing

Bump version.

```
$ rpm_py_installer/version.py
$ git add rpm_py_installer/version.py
$ git commit -m 'Bump version X.Y.Z."
```

Tagging.

```
$ git tag -a X.Y.Z
```

Upload source distribution to PyPI.

```
$ python3 setup.py sdist upload
```

Push the tag information.

```
$ git push origin X.Y.Z
```
