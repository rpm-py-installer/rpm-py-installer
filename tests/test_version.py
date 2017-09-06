"""
Tests for version.py

"""
from rpm_py_installer import version


def test_version():
    assert version.VERSION
