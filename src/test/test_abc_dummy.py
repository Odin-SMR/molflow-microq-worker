"""Dummy tests"""
import pytest

from test.testbase import system


@system
@pytest.mark.usefixtures("dockercompose")
def test_abc_dummy():
    """Dummy test to start docker environment"""
    assert True
