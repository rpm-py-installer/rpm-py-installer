# Release Notes

We do not manage release notes.

However you can see a kind of release notes by below `git` command on master branch.

For example.

```
$ git clone REPO_URL

$ cd rpm-py-installer

$ git log --graph --pretty=oneline --abbrev-commit
* 887bbe1 (HEAD -> master, tag: v0.6.0, origin/master, origin/HEAD) Bump version 0.6.0.
* 39c9eea Add Travis retry script for stable docker build. (#108)
* b91cb64 Fix environment variable names in doc (#107)
* 524aa07 Add Python 2.6 as a testing environment. (#106)
* 9739a01 Add prefix RPM_PY_ to all environment variables (#105)
* 1dce460 (tkdchen/master) Add Fedora 27 testing environment on Travis CI. (#100)
* 0460d44 Update to download an archive file on ftp.rpm.org as a primary behavior. (#99)
* 4249f9d Supress an error log when the command returns non zero status. (#98)
* ca5dead Add QAs about version mapping and updating the RPM spec file. (#96)
* 23cf317 Add explanation about the install Python binding. (#95)
* 90ecead Remove fedora:rawhide workaround from Dockerfile. (#90)
* b3d4f80 Fix for updated flake8 3.5.0. (#93)
* 4ec3c86 (tag: v0.5.0) Bump version 0.5.0.
...
```
