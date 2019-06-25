#!/usr/bin/env python3

import os
import sys

SERVICE_DICT = {
    # https://hub.docker.com/_/fedora/
    'fedora30': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:30',
            'LINT': "true",
        },
        'environment': {
            'TOXENV': 'lint-py3,lint-py2,py37,py27'
        }
    },
    'fedora30_aarch64': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'multiarch/fedora:30-aarch64',
        },
        'environment': {
            'TOXENV': 'py37'
        }
    },
    'fedora29': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:29',
        },
        # Test on no network environment for the downstream build environment.
        'network_mode': 'none',
        'command': 'make no-network-test',
    },
    'fedora28': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:28',
        },
        'environment': {
            'TOXENV': 'py36'
        }
    },
    'fedora27': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:27',
        },
        'environment': {
            'TOXENV': 'py36'
        }
    },
    'fedora26': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:26',
        },
        'environment': {
            'TOXENV': 'py35,py26'
        }
    },
    'fedora_rawhide': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:rawhide',
        },
        'environment': {
            'TOXENV': 'py37,py27'
        }
    },
    # Integration
    'intg': {
        'dockerfile': 'ci/Dockerfile-fedora',
        'args': {
            'CONTAINER_IMAGE': 'fedora:rawhide',
        },
        'environment': {
            'TOXENV': 'intg'
        }
    },
    # https://hub.docker.com/_/centos/
    'centos7': {
        'dockerfile': 'ci/Dockerfile-centos.7',
        'environment': {
            'TOXENV': 'py36,py34,py27'
        }
    },
    'centos6': {
        'dockerfile': 'ci/Dockerfile-centos.6',
        'environment': {
            'TOXENV': 'py27,py26'
        }
    },
    # https://hub.docker.com/_/ubuntu/
    'ubuntu_bionic': {
        'dockerfile': 'ci/Dockerfile-ubuntu.bionic',
        'environment': {
            'TOXENV': 'py36,py27'
        }
    },
    'ubuntu_trusty': {
        'dockerfile': 'ci/Dockerfile-ubuntu.trusty',
        'environment': {
            'TOXENV': 'py34,py27'
        }
    },
}

if len(sys.argv) < 3:
    print('Aruguments should be more than 3.')
    sys.exit(1)

task = sys.argv[1]
service = sys.argv[2]
print('Task: {}, Service: {}'.format(task, service))

ITEM_DICT = SERVICE_DICT[service]
# DOCKER = 'podman' if os.system('command -v podman') == 0 else 'docker'
DOCKER = 'docker'


def sh(cmd):
    print('CMD: {}'.format(cmd))
    if os.system(cmd) != 0:
        raise ValueError('{} failed'.format(cmd))


def build():
    cmd = '{} build --rm'.format(DOCKER)
    if 'args' in ITEM_DICT:
        for arg in ITEM_DICT['args']:
            cmd += ' --build-arg {}="{}"'.format(arg, ITEM_DICT['args'][arg])

    cmd += ' -t "rpm-py-installer_{}" -f "{}"'.format(
        service, ITEM_DICT['dockerfile'])
    cmd += ' .'
    sh(cmd)


def build_user():
    cmd = '''
{docker} build --rm \
    -t rpm-py-installer_{service}_user \
    -f ci/Dockerfile-user \
    --build-arg CONTAINER_IMAGE=rpm-py-installer_{service} \
    --build-arg USER_NAME=$(id -un) \
    --build-arg USER_ID=$(id -u) \
    --build-arg GROUP_NAME=$(id -gn) \
    --build-arg GROUP_ID=$(id -g) \
    .
'''.format(docker=DOCKER, service=service)
    sh(cmd)


def test_user():
    env_args = ''
    if 'environment' in ITEM_DICT:
        for env in ITEM_DICT['environment']:
            env_args += ' -e {}="{}"'.format(
                env, ITEM_DICT['environment'][env]
            )
    network_arg = ''
    if 'network_mode' in ITEM_DICT:
        network_arg = ' --network={}'.format(ITEM_DICT['network_mode'])
    cmd = ITEM_DICT.get('command', 'tox')
    cmd_run = '''
{docker} run --rm \
    -t \
    {env_args} \
    {network_arg} \
    -v "{cwd}:/work" \
    -w /work \
    -u "$(id -un)" \
    "rpm-py-installer_{service}_user" \
    {cmd}
'''.format(
        docker=DOCKER, env_args=env_args, network_arg=network_arg,
        cwd=os.getcwd(), service=service, cmd=cmd
    )
    sh(cmd_run)


def login():
    cmd = '''
{docker} run --rm \
    -it \
    -v "{cwd}:/work" \
    -w /work \
    -u "$(id -un)" \
    "rpm-py-installer_{service}_user" \
    bash
'''.format(docker=DOCKER, cwd=os.getcwd(), service=service)
    sh(cmd)


if task == 'build':
    build()
    build_user()
elif task == 'test':
    test_user()
elif task == 'login':
    login()
else:
    print('Task: {} not found'.format(task))
    sys.exit(1)
