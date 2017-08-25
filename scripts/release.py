import os
import sys
sys.path.append('.') # noqa
from rpm_py_installer.version import VERSION

DISP_VERSION = 'v{0}'.format(VERSION)

print('Releaseing version: {0}'.format(DISP_VERSION))


def sh_e(cmd):
    print('CMD: {0}'.format(cmd))
    if os.system(cmd) != 0:
        raise RuntimeError('Error: {0}'.format(cmd))


sh_e('git add rpm_py_installer/version.py')
sh_e("git commit -m 'Bump version {0}.'".format(VERSION))
sh_e("git tag -a '{0}' -m '{1} release'".format(DISP_VERSION, DISP_VERSION))
