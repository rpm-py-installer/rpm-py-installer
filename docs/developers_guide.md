# Developers Guide

## Tech preview

### Files

The repository has below logic files. The every logic is included in the `install.py`. The reason is to run it directory from `curl` command without `pip`. I think that is useful to debug before actual release. But it makes the source code hard to read.
If we can compress the logic from .py files to one py file including zipped binary code like [get-pip.py](https://github.com/pypa/get-pip/blob/master/get-pip.py), we can split the `install.py` to several py files.

* setup.py
* install.py

and below testing files.

* tests/test_install.py
* tests/test_integration.py

### Classes

If you run below command, you see more than 20 classes in the file.
You see comments in the source `install.py` to explain a class and the methods.

```
$ grep ^class install.py
```

### Logic

The entire logic is

* Input: `rpm` command's information and RPM source code on remote downloadin site.
* Output: built RPM Python binding package.

If the RPM's build (development) dependency `rpm-devel` package does not exist on the installed environment, `rpm-py-installer` tries to download some build depenency packages by the OS packaging manager's download commmand, to build RPM Python binding with those.

## Debugging

### Enabling your forked repository's Travis CI

It's useful to enable your forked repository's Travis CI.
Fork this repository, and click sync account from GitHub on the [Travis repositories page](https://travis-ci.org/account/repositories), to see forked `your_name/rpm-py-installer` repository.
Then enable your repository's Travis CI on https://travis-ci.org/your_name/rpm-py-installer .

Create your new branch such as `feature/something` for your pull-request.

You need to comment out below lines to run your Travis CI on your branch, when pushing the commit to your repository's branch.

.traivs.yml

```
branches:
  only:
    - master
```

You can check your commit passes the CI before sending the pull-request.

### Working on your local environment with container testing enviroments

You can also test on your local without CI. See `.travis.yml`, `Makefile` and `docker-compose.yml`.

Below is to build on the service's environment.
The service downloads and builds the container environment.

```
$ make SERVICE=<SERVICE>
```

For example to build Fedora rawhide case.

```
$ make SERVICE=fedora_rawhide
```

Below is to test on the service's environment.

Please note that the source directory are volume mounted with the container.
When running `make test`, it updates working files with root permission.
Sorry for inconvenience. The way to clean the files removing working files is to run `sudo git clean -fdx` on the host's directory.

```
$ make test SERVICE=<SERVICE>
```

Below is to login on the service's container environment.


```
$ make login SERVICE=<SERVICE>
```

```
$ make login SERVICE=fedora_rawhide
docker run -it rpm-py-installer_fedora_rawhide bash
TOXENV:
[root@a1e651c7b69b build]#
```

### Working on your local environment without container testing enviroments

If you have a Linux environment to run it, easy way to run test is to run `tox`.
Install `tox` on your environment. Then you can check `tox` tasks like this.
The `lint-*` are tasks for lint. The `*-cov` are tasks for the coverage.

```
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

Run below command to run on specific Python.

```
$ tox -e py36
...
tests/test_version.py::test_version PASSED                                             [100%]

==================== 124 passed, 3 skipped, 2 deselected in 98.44 seconds ====================
__________________________________________ summary ___________________________________________
  py36: commands succeeded
  congratulations :)
```

Run below commadn to run specific test case.

```
$ tox -e py36 -- "tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed]"
...
tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed] PASSED   [100%]

================================== 1 passed in 6.16 seconds ==================================
__________________________________________ summary ___________________________________________
  py36: commands succeeded
  congratulations :)
```


`tox -- -s` option is useful for debug to see the stdout of the program.

```
$ tox -e py36 -- -s "tests/test_install.py::test_app_run_is_ok[rpm-devel and popt-devel installed]"
```

You can debug a specific test case outputting debug log, by adding or editing `@mock.patch.object(Log, 'verbose', new=True)` like this.

```
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
