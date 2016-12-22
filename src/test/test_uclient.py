import json
import pytest

from uclient.uclient import UClient, UClientError, Job
from test.testbase import BaseWithWorkerUser, system


class BaseTestUClient(BaseWithWorkerUser):
    def setUp(self):
        super(BaseTestUClient, self).setUp()
        self._credentials = {"username": self._token,
                             "password": ''}

    def get_client(self, credentials=None):
        credentials = (credentials if credentials is not None
                       else self._credentials)
        return UClient(self._apiroot, verbose=True,
                       time_between_retries=0.01, **credentials)


@system
@pytest.mark.usefixtures("dockercompose")
class TestErrors(BaseTestUClient):

    def test_bad_project_name(self):
        bad_names = ['', '1', 'test;']
        client = self.get_client()
        for name in bad_names:
            with self.assertRaises(UClientError):
                client.get_project_uri(project=name)

    def test_api_exception(self):
        """Test api exception"""
        api = self.get_client()
        with self.assertRaises(UClientError):
            api.update_output('bad url', 'out')


class BaseTestWithInsertedJob(BaseTestUClient):

    def setUp(self):
        super(BaseTestWithInsertedJob, self).setUp()
        self._delete_test_project()
        self._insert_test_jobs()

    def tearDown(self):
        self._delete_test_project()


@system
@pytest.mark.usefixtures("dockercompose")
class TestCredentials(BaseTestWithInsertedJob):

    def test_credentials_from_file(self):
        """Test load of credentials from file"""
        credentials_file = '/tmp/credentials.json'
        with open(credentials_file, 'w') as out:
            out.write(json.dumps(self._credentials))
        api = self.get_client({'credentials_file': credentials_file})
        job = Job.fetch(api, job_type='test_type')
        job.send_status('test')

    def test_bad_credentials(self):
        """Test invalid and empty credentials"""
        # The guy below should use different uris:
        credentials = {"username": "snoopy", "password": "ace"}
        api = self.get_client(credentials)
        with self.assertRaises(UClientError):
            Job.fetch(api, job_type='test_type')

        try:
            Job.fetch(api, job_type='test_type')
            raise AssertionError('Should have excepted!')
        except UClientError as e:
            self.assertEqual(e.status_code, 401)

        # No credentials provided
        api = self.get_client({})
        with self.assertRaises(UClientError):
            Job.fetch(api, job_type='test_type')


@system
@pytest.mark.usefixtures("dockercompose")
class TestJob(BaseTestWithInsertedJob):

    def test_job(self):
        """Test fetch, claim and update status/output"""
        api = self.get_client()

        r = api.get_job_list(self._project)
        self.assertEqual(r.status_code, 200)

        job = Job.fetch(api)
        self.assertFalse(job.claimed)
        job = Job.fetch(api, project=self._project)
        self.assertFalse(job.claimed)

        job.claim()
        self.assertTrue(job.claimed)
        job.claim()
        self.assertTrue(job.claimed)

        job.send_status('Claimed job')

        self.assertEqual(job.url_source, self.TEST_URL)
        self.assertEqual(job.url_target, self.TEST_URL)
        self.assertEqual(job.url_image, None)
        self.assertEqual(job.environment, {})

        job.send_status("Got data")

        api.update_output(job.url_output, "Processing...")
        job.send_status("Work done")
