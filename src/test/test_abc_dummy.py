"""Dummy tests"""
import pytest


@pytest.mark.system
def test_abc_dummy(microq_service):
    """Dummy test to start docker environment"""
    assert True
