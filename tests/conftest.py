"""Common functions and a list of pytest.fixture here."""

import os
import sys
from contextlib import contextmanager

import pytest

install_path = os.path.abspath('install.py')
sys.path.insert(0, install_path)

pytest_plugins = ['helpers_namespace']


@pytest.fixture
def install_script_path():
    return install_path


@pytest.helpers.register
@contextmanager
def reset_dir():
    current_dir = os.getcwd()
    try:
        yield
    finally:
        os.chdir(current_dir)


@pytest.helpers.register
@contextmanager
def pushd(target_dir):
    current_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        yield
    finally:
        os.chdir(current_dir)
