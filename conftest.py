import os

import requests
from requests.exceptions import RequestException
import pytest

WAIT_FOR_SERVICE_TIME = 60 * 5
PAUSE_TIME = 0.1


def pytest_addoption(parser):
    """Adds the integrationtest option"""
    parser.addoption(
        "--runslow", action="store_true", help="run slow tests")
    parser.addoption(
        "--runsystem", action="store_true", help="run system tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--runslow'):
        skip_slow = pytest.mark.skip(reason='need --runslow option to run')
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if not config.getoption('--runsystem'):
        skip_system = pytest.mark.skip(reason='need --runsystem option to run')
        for item in items:
            if "system" in item.keywords:
                item.add_marker(skip_system)


def is_responsive(baseurl):
    try:
        r = requests.get(
            "{}/rest_api/v4/projects".format(baseurl),
            timeout=5,
        )
        r.raise_for_status()
    except RequestException:
        return False
    return True


@pytest.fixture(scope='session')
def docker_compose_file(pytestconfig):
    return os.path.join(
        os.path.dirname(__file__),
        'docker-compose.systemtest.yml',
    )


@pytest.fixture(scope='session')
def microq_service(docker_ip, docker_services):
    port = docker_services.port_for('webapi', 5000)
    url = "http://localhost:{}".format(port)
    docker_services.wait_until_responsive(
        timeout=WAIT_FOR_SERVICE_TIME,
        pause=PAUSE_TIME,
        check=lambda: is_responsive(url),
    )
    return url
