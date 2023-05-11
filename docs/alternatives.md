# Alternative ways of RPM Python binding

In this document, we introduce alternative ways that may solve your facing challenges.

## Using venv --system-site-packages option

This is the way of using `python -m venv` or `virtualenv` `--system-site-packages` option to give the virtual environment access to the system site packages. It was confirmed on Fedora Linux 37.

Install the system RPM Python binding package.

```
$ sudo dnf install python3-rpm

$ rpm -q python3-rpm
python3-rpm-4.18.0-1.fc37.x86_64

$ pip list | grep '^rpm '
rpm                  4.18.0

$ python -m venv --help
...
  --system-site-packages
                        Give the virtual environment access to the system site-packages
                        dir.
...
```

Then you can load the system `rpm` PyPI package in the virtual environment.

```
$ python -m venv ./venv --system-site-packages

$ source venv/bin/activate

(venv) $ pip list | grep ^rpm
rpm                  4.18.0
...
```

## Using rpm-shim module from PyPI

See [the rpm PyPI page](https://pypi.org/project/rpm/). It replaces itself with system RPM Python bindings when imported in a virtual environment.
