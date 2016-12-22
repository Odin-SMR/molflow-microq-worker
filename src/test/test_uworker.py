import os
import json
from time import time, sleep
import threading
import unittest

import requests
import pytest
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
from werkzeug.wrappers import Request, Response

from test.testbase import (
    BaseWithWorkerUser, TEST_DATA_DIR, disable, slow, system)

from utils.defs import JOB_STATES
from utils import logs
from utils.docker_util import in_docker
from utils import docker_util
from uworker import uworker

# TODO: Start a local registry while testing?
TEST_IMAGE = 'alpine:3.4'  # ~5Mb


class BaseUWorkerTest(BaseWithWorkerUser):
    in_docker = None

    @property
    def env(self):
        """Return dict with env variables that should be set"""
        raise NotImplementedError

    def setUp(self):
        for k, v in self.env.items():
            os.environ[k] = v
        self._insert_test_jobs()
        self.orig_in_docker = in_docker
        docker_util.in_docker = lambda: self.in_docker

    def tearDown(self):
        docker_util.in_docker = self.orig_in_docker
        self._delete_test_project()

    def _test_bad_config(self):
        optional = ['UWORKER_EXTERNAL_API_USERNAME',
                    'UWORKER_EXTERNAL_API_PASSWORD']
        for k in self.env:
            v = os.environ.pop(k)
            if k in optional:
                uworker.UWorker()
            else:
                print('Mandatory: %s' % k)
                with self.assertRaises(uworker.UWorkerError):
                    uworker.UWorker()
            os.environ[k] = v

    def _run_once(self, expected_jobs_count=0):
        uworker.UWorker.IDLE_SLEEP = .01
        uworker.UWorker.ERROR_SLEEP = .01
        w = uworker.UWorker()
        w.alive = True
        self.assertEqual(w.job_count, 0)
        w.run(only_once=True)
        self.assertEqual(w.job_count, expected_jobs_count)
        # TODO: Check that result and output from job were stored.


@disable
@system
@pytest.mark.usefixtures("dockercompose")
class TestUWorkerInDocker(BaseUWorkerTest):
    """Test worker that is running in a docker container"""

    in_docker = True

    @property
    def env(self):
        return {
            'UWORKER_HOSTNAME': 'testhost',
            'HOSTNAME': 'testcontainer',
            'UWORKER_JOB_CMD': 'echo test',
            'UWORKER_JOB_TYPE': 'test',
            'UWORKER_JOB_API_ROOT': self._apiroot,
            'UWORKER_JOB_API_PROJECT': self._project,
            'UWORKER_JOB_API_USERNAME': self._token,
            'UWORKER_JOB_API_PASSWORD': "",
            'UWORKER_EXTERNAL_API_USERNAME': 'test',
            'UWORKER_EXTERNAL_API_PASSWORD': 'test',
        }

    def test_bad_config(self):
        """Test missing environment variables"""
        self._test_bad_config()

    def test_run(self):
        """Test one worker run"""
        self._run_once(expected_jobs_count=1)

    def test_exit_code(self):
        """Test job command that return failure"""
        os.environ['UWORKER_JOB_CMD'] = 'ls test_exit_code'
        self._run_once(expected_jobs_count=1)

    def test_api_failure(self):
        """Test bad api url and password"""
        os.environ['UWORKER_JOB_API_USERNAME'] = 'wrong'
        self._run_once(expected_jobs_count=0)

        os.environ['UWORKER_JOB_API_ROOT'] = 'wrong'
        self._run_once(expected_jobs_count=0)

    def test_main(self):
        """Test to provide an input url argument"""
        uworker.main(['https://example.com/test'])


@system
@pytest.mark.usefixtures("dockercompose")
class TestUWorkerOnHost(BaseUWorkerTest):
    """Test worker that is running on the host"""

    in_docker = False

    _test_jobs = [
        {'id': '42', 'type': 'test_type',
         'source_url': 'echo',
         'target_url': BaseUWorkerTest.TEST_URL}
    ]

    @property
    def env(self):
        return {
            'HOSTNAME': 'testcontainer',
            'UWORKER_JOB_API_ROOT': self._apiroot,
            'UWORKER_JOB_API_USERNAME': self._token,
            'UWORKER_JOB_API_PASSWORD': "",
            'UWORKER_EXTERNAL_API_USERNAME': 'test',
            'UWORKER_EXTERNAL_API_PASSWORD': 'test',
        }

    def setUp(self):
        super(TestUWorkerOnHost, self).setUp()
        r = requests.put(
            BaseWithWorkerUser._apiroot + '/v4/' + BaseWithWorkerUser._project,
            auth=self._auth, json={'processing_image_url': TEST_IMAGE})
        self.assertEqual(r.status_code, 204)

    def test_bad_config(self):
        """Test missing environment variables"""
        self._test_bad_config()

    def test_run(self):
        """Test one worker run"""
        self._run_once(expected_jobs_count=1)

    def test_exit_code(self):
        """Test job command that return failure"""
        error_job = {
            'id': '43', 'type': 'test_type',
            'source_url': 'ls test_exit_code',
            'target_url': BaseUWorkerTest.TEST_URL}
        self.assertEqual(self._insert_job(error_job), 201)
        self._run_once(expected_jobs_count=1)
        self._run_once(expected_jobs_count=1)


class BaseExecutorTest(unittest.TestCase):

    @staticmethod
    def callback(msg):
        """Process stdout and stderr are sent to this function"""
        print(repr(msg))
        BaseExecutorTest.callback.last_message = msg

    def setUp(self):
        self.log = logs.get_logger('unittest', to_file=False, to_stdout=True)


class TestCommandExecutor(BaseExecutorTest):

    def test_execute_success(self):
        """Test execution that succeeds"""
        ce = uworker.CommandExecutor('Test', ['echo'], self.log)
        return_code, _ = ce.execute(['test_execute_success'],
                                    self.callback)
        self.assertEqual(return_code, 0)
        self.assertTrue('test_execute_success' in self.callback.last_message)

    def test_execute_failure(self):
        """Test execution that fails"""
        ce = uworker.CommandExecutor('Test', ['rm'], self.log)
        return_code, _ = ce.execute(['this.file.should.not.exist'],
                                    self.callback)
        self.assertEqual(return_code, 1)

    def test_timeout(self):
        """Test that process is killed if timeout"""
        ce = uworker.CommandExecutor('Test', ['sleep'], self.log)
        return_code, _ = ce.execute(['5'],
                                    self.callback, timeout=1, kill_after=1)
        self.assertNotEqual(return_code, 0)
        self.assertTrue('Killed Test process' in self.callback.last_message)


@slow
class TestDockerExecutor(BaseExecutorTest):

    def test_image_pull(self):
        """Test pull of docker image"""
        de = uworker.DockerExecutor('Test', TEST_IMAGE, self.log)
        if de.image_exists():
            ce = uworker.CommandExecutor('Remove image', ['docker', 'rmi'],
                                         self.log)
            ce.execute([TEST_IMAGE], self.callback)
        self.assertFalse(de.image_exists())
        de.pull_image(self.callback)
        self.assertTrue(de.image_exists())

    def test_execute_success(self):
        """Test execution that succeeds"""
        de = uworker.DockerExecutor('Test', TEST_IMAGE, self.log)
        return_code, _ = de.execute(['echo', 'test_execute_success'],
                                    self.callback)
        self.assertEqual(return_code, 0)
        self.assertTrue('test_execute_success' in self.callback.last_message)

    def test_environment_variables(self):
        """Test provisioning of environment variables to container"""
        de = uworker.DockerExecutor(
            'Test', TEST_IMAGE, self.log,
            environment={'TESTENV': 'test_environment_variables'})
        return_code, _ = de.execute(['env'], self.callback)
        self.assertEqual(return_code, 0)
        self.assertTrue(
            'test_environment_variables' in self.callback.last_message)

    def test_execute_failure(self):
        """Test execution that fails"""
        de = uworker.DockerExecutor('Test', TEST_IMAGE, self.log)
        return_code, _ = de.execute(['rm', 'this.file.should.not.exist'],
                                    self.callback)
        self.assertEqual(return_code, 1)


@system
@pytest.mark.usefixtures("dockercompose")
@unittest.skipIf(not in_docker(),
                 'Must be run in a container with a running uworker')
class TestQsmrJob(BaseWithWorkerUser):
    JOB_ID = '42'
    _apiroot = 'http://webapi:5000/rest_api'
    _project = 'testproject'

    ODINMOCK_HOST = 'localhost'
    ODINMOCK_PORT = 8888

    @property
    def odin_mock_root(self):
        return 'http://%s:%s' % (self.ODINMOCK_HOST, self.ODINMOCK_PORT)

    def setUp(self):
        super(TestQsmrJob, self).setUp()
        self.odin_api = MockOdinAPI(self.ODINMOCK_HOST, self.ODINMOCK_PORT)
        self.odin_api.start()

    def tearDown(self):
        super(TestQsmrJob, self).tearDown()
        requests.get(self.odin_mock_root + '?shutdown=1')

    def test_success(self):
        self._test_job()

    def test_failure(self):
        self._test_job(should_succeed=False)

    def _test_job(self, should_succeed=True):
        """Start a fake odin api server and run a qsmr job"""
        self._insert_qsmr_job()
        # Wait for result
        start = time()
        max_wait = 60*3
        job_status = self._get_job_status()
        while (job_status not in (JOB_STATES.finished, JOB_STATES.failed) and
               not self.odin_api.result):
            sleep(1)
            if time() - start > max_wait:
                break
            job_status = self._get_job_status()
        if self.odin_api.result:
            print('Result: %r' % self.odin_api.result.keys())
        else:
            print('No results!')

        # Wait for job to finish
        start = time()
        max_wait = 10
        job_status = self._get_job_status()
        while job_status == JOB_STATES.started:
            sleep(1)
            if time() - start > max_wait:
                break
            job_status = self._get_job_status()

        print('Job status: %r' % job_status)
        print('Job output: %r' % self._get_job_output())
        print('Job results should have been written to %s' % os.path.join(
            TEST_DATA_DIR, 'odin_result.json'))
        if should_succeed:
            self.assertEqual(job_status, JOB_STATES.finished)
            self.assertTrue(self.odin_api.result)
        else:
            self.assertEqual(job_status, JOB_STATES.failed)
            self.assertIsNone(self.odin_api.result)

    def _insert_qsmr_job(self):
        self._insert_job(
            {'id': self.JOB_ID, 'type': 'qsmr',
             'source_url': self.odin_mock_root,
             'target_url': self.odin_mock_root})

    def _get_job_status(self):
        r = requests.get(
            self._apiroot + '/v4/{}/jobs/{}/status'.format(
                self._project, self.JOB_ID),
            auth=(self._username, self._password))
        return r.json()['Status']

    def _get_job_output(self):
        r = requests.get(
            self._apiroot + '/v4/{}/jobs/{}/output'.format(
                self._project, self.JOB_ID),
            auth=(self._username, self._password))
        return r.json()


class MockOdinAPI(threading.Thread):
    """A really basic HTTP server that listens on (host, port) and serves
    static odin data and accepts posts.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.load_data()
        self.result = None
        super(MockOdinAPI, self).__init__()

    def load_data(self):
        with open(os.path.join(TEST_DATA_DIR, 'odin_log.json')) as inp:
            self.log = json.loads(inp.read())
        self.log['Info']['URLS']['URL-spectra'] = 'http://%s:%s?spectra=1' % (
            self.host, self.port)
        with open(os.path.join(TEST_DATA_DIR, 'odin_spectra.json')) as inp:
            self.spectra = json.loads(inp.read())

    def handle_request(self, environ, start_response):
        try:
            request = Request(environ)
            if request.method.lower() == 'get':
                if request.args.get('shutdown'):
                    self.shutdown_server(environ)
                elif request.args.get('spectra'):
                    response = Response(json.dumps(self.spectra), headers={
                        'Content-Type': 'application/json'})
                else:
                    response = Response(json.dumps(self.log), headers={
                        'Content-Type': 'application/json'})
            elif request.method.lower() == 'post':
                self.result = json.loads(request.get_data(
                    cache=False, as_text=True))
                with open(os.path.join(
                        TEST_DATA_DIR, 'odin_result.json'), 'w') as out:
                    out.write(json.dumps(self.result))
                response = Response('thanks!')
            else:
                response = Response(':(', 415)
        except Exception as e:
            print('Mock odin excepted: %s' % e)
            raise
        return response(environ, start_response)

    def run(self):
        server = BaseWSGIServer(self.host, self.port, self.handle_request,
                                _QuietHandler)
        server.log = lambda *args, **kwargs: None
        server.serve_forever()

    @staticmethod
    def shutdown_server(environ):
        if 'werkzeug.server.shutdown' not in environ:
            raise RuntimeError('Not running the development server')
        environ['werkzeug.server.shutdown']()


class _QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        """Suppress request logging so as not to pollute application logs."""
        pass
