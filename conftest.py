"""Unitttests"""

from time import sleep, time
from subprocess import check_output, Popen
import requests
import pytest


def pytest_addoption(parser):
    """Adds the integrationtest option"""
    parser.addoption(
        "--runslow", action="store_true", help="run slow tests")
    parser.addoption(
        "--runsystem", action="store_true", help="run system tests")
    parser.addoption(
        "--rundisabled", action="store_true", help="run disabled tests")
    parser.addoption(
        "--no-system-restart", action="store_true",
        help="do not restart the system")


def call_docker_compose(cmd, root_path, args=None, wait=True):
    cmd = ['docker-compose', cmd] + (args or [])
    popen = Popen(cmd, cwd=root_path)
    if wait:
        popen.wait()
    return popen


@pytest.yield_fixture(scope='session')
def dockercompose():
    """Set up the full system"""
    root_path = check_output(['git', 'rev-parse', '--show-toplevel']).strip()

    if not pytest.config.getoption("--no-system-restart"):
        call_docker_compose('stop', root_path)
        call_docker_compose('rm', root_path, args=['--force'])
        call_docker_compose('pull', root_path)
        call_docker_compose('build', root_path)

    args = ['--abort-on-container-exit', '--remove-orphans']
    system = call_docker_compose('up', root_path, args=args, wait=False)

    # Wait for webapi and database
    max_wait = 60*5
    start_wait = time()
    while True:
        exit_code = system.poll()
        if exit_code is not None:
            call_docker_compose('stop', root_path)
            assert False, 'docker-compose exit code {}'.format(exit_code)
        try:
            r = requests.get(
                'http://localhost:5000/rest_api/v4/projects',
                timeout=1)
            if r.status_code == 200:
                break
            else:
                sleep(1)
        except requests.ConnectionError:
            sleep(1)
        if time() > start_wait + max_wait:
            call_docker_compose('stop', root_path)
            if system.poll() is None:
                system.kill()
                system.wait()
            assert False, 'Could not access webapi after %d seconds' % max_wait

    yield system.pid

    if not pytest.config.getoption("--no-system-restart"):
        call_docker_compose('stop', root_path)
        if system.poll() is None:
            system.kill()
            system.wait()
