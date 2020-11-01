# Developer's Guide

## Tech preview

### Files

The repository has the following logic files:

* setup.py
* install.py

All logic is included in `install.py`. The reason for that is to be able to run it directly via the `curl` command without `pip`. I think that is useful to debugging before an actual release. But it makes the source code hard to read.
If we can compress the logic from `.py` files to one `.py` file including zipped binary code like [get-pip.py](https://github.com/pypa/get-pip/blob/master/get-pip.py), we can split `install.py` to several `*.py` files.

The following files include the tests:

* [tests/test_install.py](../tests/test_install.py)
* [tests/test_version.py](../tests/test_version.py)
* [tests/test_integration.py](../tests/test_integration.py)
* [tests/test_install_fedora.py](../tests/test_install_fedora.py)
* [tests/test_install_suse.py](../tests/test_install_suse.py)

### Classes

If you run the following command, you can see more than 20 classes in the file.

``` ShellSession
$ grep ^class install.py
```

The comments in the source `install.py` explain a class and the methods.

### Logic

The entire logic is:

* Input: `rpm` command's information and RPM source code on remote download site.
* Output: built RPM Python binding package.

If the RPM's build (development) dependency `rpm-devel` package does not exist on the installed environment, `rpm-py-installer` tries to download some build dependencies via the OS package manager's download command, to build the RPM Python binding with those.

## Debugging

### Enabling your forked repository's Travis CI

It's useful to enable Travis CI for your forked repository.
After forking this repository, click sync account from GitHub on the [Travis repositories page](https://travis-ci.org/account/repositories) and find the `your_name/rpm-py-installer` repository.
Then enable your repository's Travis CI on https://travis-ci.org/your_name/rpm-py-installer .

Create your new branch such as `feature/something` for your pull-request.

This allows you to verify that your changes pass the CI, before submitting a pull-request.

### Working in a local environment with containers for testing

You can also run the test on your local machine without Travis CI. The main `make` argument is `DOCKERFILE`, `IMAGE` and `TOXENV`. See `.travis.yml` and `Makefile` for detail.

Run the following command to build the container environment:

``` ShellSession
$ make DOCKERFILE=<DOCKERFILE> IMAGE=<IMAGE> TOXENV=<TOXENV>
```

For example to build Fedora rawhide case:

``` ShellSession
$ make DOCKERFILE="ci/Dockerfile-fedora" IMAGE="fedora:rawhide" TOXENV="py3"
```

As the above values are the default values of the `Makefile`, the following command is equivalent.

```
$ make
```

Run the tests in the container via:

``` ShellSession
$ make test IMAGE=<IMAGE>
```

Please note that the source directory is volume mounted inside the container.
When running `make test`, it updates the working files with root permission.
Sorry for inconveniences, the simplest way to clean the files is to run `sudo git clean -fdx` in the host's directory.

Use the commands below to login into the case's container environment:

``` ShellSession
$ make login IMAGE=<IMAGE>
```

``` ShellSession
$ make login IMAGE=fedora:rawhide
docker run -it rpm-py-installer_fedora_rawhide bash
TOXENV:
[root@a1e651c7b69b work]#
```

### Working in a local environment without containers for testing

If you have a Linux environment at hands, then an easy way to run the tests is use `tox`.
Install `tox` on your machine (either via `pip` or your distribution's package manager). Then you can check `tox` tasks as follows:

``` ShellSession
$ tox -l
lint-py3
lint-py2
py37-cov
py37
py36-cov
py36
py35-cov
py35
py34-cov
py34
py27-cov
py27
py26-cov
py26
```

The `lint-*` are tasks for linting. The `*-cov` tasks obtain the test coverage.

Run the command below to test a specific Python version:

``` ShellSession
$ tox -e py36
...
tests/test_version.py::test_version PASSED                                             [100%]

==================== 124 passed, 3 skipped, 2 deselected in 98.44 seconds ====================
__________________________________________ summary ___________________________________________
  py36: commands succeeded
  congratulations :)
```

Run the following command to only run specific test case:

``` ShellSession
$ tox -e py36 -- "tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed]"
...
tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed] PASSED   [100%]

================================== 1 passed in 6.16 seconds ==================================
__________________________________________ summary ___________________________________________
  py36: commands succeeded
  congratulations :)
```


The `tox -- -s` option is useful for debugging to see the stdout of the program:

``` ShellSession
$ tox -e py36 -- -s "tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed]"
```

You can debug a specific test case outputting debug log, by adding or editing `@mock.patch.object(Log, 'verbose', new=True)` like this.

``` ShellSession
$ git diff
diff --git a/tests/test_install.py b/tests/test_install.py
index 255f458..2cf7a85 100644
--- a/tests/test_install.py
+++ b/tests/test_install.py
@@ -1286,7 +1286,7 @@ def test_app_run_is_ok_on_download_by_rpm_py_version(app, rpm_py_version):
         'RPM downloadable',
     ]
 )
-@mock.patch.object(Log, 'verbose', new=False)
+@mock.patch.object(Log, 'verbose', new=True)
 @pytest.mark.skipif(pytest.helpers.helper_is_debian(),
                     reason='Only Linux Fedora.')
 def test_app_run_is_ok(
```

## Releasing

Bump version `X.Y.Z`.

``` ShellSession
$ vi rpm_py_installer/version.py
```

Do `git add`, `git commit` and tag:

``` ShellSession
$ python3 scripts/release.py
```

Upload source distribution to PyPI.
Run it on virtualenv, because right now install process is run.

``` ShellSession
$ source venv/bin/activate
(venv) $ python3 setup.py sdist upload
(venv) $ deactivate
```

Push the commit and tag information to the upstream repository:

``` ShellSession
$ git push origin master
$ git push origin vX.Y.Z
```
