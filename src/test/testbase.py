"""Base classes for tests of uService"""
import os
import unittest
import requests
import pytest


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'testdata')


class BaseSystemTest(unittest.TestCase):

    TEST_URL = 'http://example.com'

    _adminuser = 'admin'
    _adminpw = 'sqrrl'
    _project = 'project'
    _username = 'worker1'
    _password = 'sqrrl'

    _test_jobs = [
        {'id': '42', 'type': 'test_type',
         'source_url': TEST_URL,
         'target_url': TEST_URL}
    ]

    @pytest.fixture(autouse=True)
    def apiroot(self, microq_service):
        self._apiroot = "{}/rest_api".format(microq_service)

    def tearDown(self):
        self._delete_test_project()

    def _delete_test_project(self, project=None):
        requests.delete(
            self._apiroot + '/v4/{}'.format(project or self._project),
            auth=(self._token or self._username, self._password))

    @property
    def _auth(self):
        if self._token:
            return (self._token, '')
        return (self._username, self._password)

    def _insert_test_jobs(self, project=None):
        # TODO: Only inserting one job because authentication takes ~0.5 secs
        for job in self._test_jobs[:1]:
            status_code = self._insert_job(job, project=project)
            assert status_code == 201, status_code

    def _insert_job(self, job, project=None):
        """Insert job and set status"""
        job = job.copy()
        id = job['id']
        worker = job.pop('worker', self._username)
        processing_time = job.pop('processing_time', 0)
        added = job.pop('added_timestamp', None)
        claimed = job.pop('claimed_timestamp', None)
        finished = job.pop('finished_timestamp', None)
        failed = job.pop('failed_timestamp', None)
        auth = (self._token or self._username, self._password)
        job.pop('claimed', None)
        job.pop('current_status', None)
        r = requests.post(
            self._apiroot + '/v4/{}/jobs{}'.format(
                project or self._project,
                ('?now=' + added) if added else ''),
            json=job, auth=auth)
        if r.status_code != 201:
            return r.status_code
        if claimed:
            data = {'Worker': worker}
            r_ = requests.put(
                self._apiroot + '/v4/{}/jobs/{}/claim?now={}'.format(
                    project or self._project, id, claimed),
                auth=auth, json=data)
            assert r_.status_code == 200, r_.status_code
        if finished or failed:
            if finished:
                status = {'Status': 'FINISHED'}
            else:
                status = {'Status': 'FAILED'}
            status['ProcessingTime'] = processing_time
            r_ = requests.put(
                self._apiroot + '/v4/{}/jobs/{}/status?now={}'.format(
                    project or self._project, id, finished or failed),
                auth=auth, json=status)
            assert r_.status_code == 200, r_.status_code
        return r.status_code

    def _insert_worker_user(self):
        r = requests.post(self._apiroot + "/admin/users",
                          headers={'Content-Type': "application/json"},
                          json={"username": self._username,
                                "password": self._password},
                          auth=(self._adminuser, self._adminpw))
        assert r.status_code == 201, r.status_code
        return r.json()['userid']

    def _get_worker_token(self):
        r = requests.get(self._apiroot + "/token",
                         auth=(self._username, self._password))
        assert r.status_code == 200, r.status_code
        return r.json()['token']

    def _delete_user(self, userid):
        requests.delete(self._apiroot + "/admin/users/{}".format(userid),
                        auth=(self._adminuser, self._adminpw))


class BaseWithWorkerUser(BaseSystemTest):

    @pytest.fixture(autouse=True)
    def myworker(self, apiroot):
        self.worker_userid = self._insert_worker_user()
        self._token = self._get_worker_token()
        yield
        self._delete_user(self.worker_userid)
        self._token = None


class BaseInsertedJobs(BaseWithWorkerUser):

    @pytest.fixture(autouse=True)
    def myjobs(self, myworker):
        self._insert_test_jobs()
