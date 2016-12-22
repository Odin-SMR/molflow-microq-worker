import json
import urllib
from time import sleep
import requests

from utils.validate import validate_project_name


class UClientError(Exception):
    def __init__(self, reason, status_code=None):
        self.status_code = status_code
        if status_code:
            msg = '{} {}'.format(status_code, reason)
        else:
            msg = reason
        super(UClientError, self).__init__(msg)


class UClient(object):
    """API to the micro service

    The client is mostly adapted to suit the needs of uworker.
    """

    def __init__(self, apiroot, username=None, password=None,
                 credentials_file=None, verbose=False, retries=5,
                 time_between_retries=60):
        """
        Init the api client.

        Args:
          apiroot (str): Root url to the micro service.
          project (str): Name of the processing project.
          username (str): Micro service username.
          password (str): Micro service password
          credentials_file (str): Path to file that contains micro service
            credentials. This is an alternative to passing username/password
            as arguments.
          verbose (bool): If True, print api responses.
          retries (int): Retry the requests to the micro service at most This
            many times.
          time_between_retries (int): Number of seconds between the retry
            requests.
        """
        self.uri = apiroot.strip('/')
        self.verbose = verbose
        self.credentials = self._get_credentials(
            username, password, credentials_file)
        self.token = None
        self.retries = retries
        self.time_between_retries = time_between_retries

    def get_project_uri(self, project):
        if not validate_project_name(project):
            raise UClientError('Unsupported project name')
        return self.uri + '/v4/{}'.format(project)

    def renew_token(self):
        """
        Renew token for token based authorization.
        """
        url = self.uri + "/token"
        auth = (self.credentials['username'], self.credentials['password'])
        r = self._call_api(url, renew_token=False, auth=auth)
        self.token = r.json()['token']

    def _load_credentials(self, filename="credentials.json"):
        """
        Load credentials from credentials file.

        Not very secure.
        """
        with open(filename) as fp:
            credentials = json.load(fp)
        if self.verbose:
            print("loaded credentials from '{0}'".format(filename))
        return credentials

    def _get_credentials(self, username, password, credentials_file):
        """
        Get credentials from arguments or file.

        If both file and user has been supplied, use the manually entered
        user and password.
        """
        if username is not None:
            return {"username": username, "password": password}
        elif credentials_file is not None:
            return self._load_credentials(credentials_file)
        else:
            return None

    def get_job_list(self, project):
        """Request list of jobs from server."""
        return self._call_api(self.get_project_uri(project) + "/jobs")

    def fetch_job(self, job_type=None, project=None):
        """Request an unprocessed job from server."""
        if project:
            url = self.get_project_uri(project) + "/jobs/fetch"
        else:
            url = self.uri + '/v4/projects/jobs/fetch'
        if job_type:
            url += '?{}'.format(urllib.urlencode({'type': job_type}))
        return self._call_api(url)

    def claim_job(self, url, worker_name):
        """Claim job from server"""
        # TODO: Worker node info
        return self._call_api(url, 'PUT', json={"Worker": worker_name})

    def update_output(self, url, output):
        """Update output of job."""
        return self._call_api(url, 'PUT', json={'Output': output},
                              headers={'Content-Type': "application/json"})

    def update_status(self, url, status, processing_time=None):
        """Update status of job."""
        data = {'Status': status,
                'ProcessingTime': processing_time}
        return self._call_api(url, 'PUT', json=data,
                              headers={'Content-Type': "application/json"})

    def _call_api(self, url, method='GET', renew_token=True, auth=None,
                  **kwargs):
        """Call micro service.

        Returns:
           r (requests.Response): The api response.
        Raises:
           UClientError: When api call failes.
        """
        if auth is None:
            auth = self.auth
        response = None
        for _ in range(self.retries):
            try:
                response = getattr(
                    requests, method.lower())(url, auth=auth, **kwargs)
                break
            except Exception as e:
                # TODO: log exception
                sleep(self.time_between_retries)
        if response is None:
            raise UClientError('API call to %r failed: %s' % (url, e))
        if self.verbose:
            print(response.text)
        if renew_token and response.status_code == 401:
            self.renew_token()
            return self._call_api(
                url, method=method, renew_token=False, **kwargs)
        if response.status_code > 299:
            raise UClientError(response.reason, response.status_code)
        return response

    @property
    def auth(self):
        if not self.credentials:
            raise UClientError('No credentials provided')
        if not self.token:
            self.renew_token()
        return (self.token, '')


class Job(object):
    def __init__(self, data, api):
        """Init a job.

        Args:
           data (dict): Job data as returned from api.
           api (UClient): API to the micro service.
        """
        self.data = data
        self.api = api
        self.claimed = False

    @classmethod
    def fetch(cls, api, job_type=None, project=None):
        r = api.fetch_job(job_type=job_type, project=project)
        return cls(r.json(), api)

    @property
    def url_claim(self):
        """Claim job by calling this url"""
        return self.data["Job"]["URLS"]["URL-claim"]

    @property
    def url_status(self):
        """Send status of job to this url"""
        return self.data["Job"]["URLS"]["URL-status"]

    @property
    def url_output(self):
        """Send output from job to this url"""
        return self.data["Job"]["URLS"]["URL-output"]

    @property
    def url_source(self):
        """External url to get input data to job"""
        return self.data["Job"]["URLS"]["URL-source"]

    @property
    def url_target(self):
        """External url to send results from job"""
        return self.data["Job"]["URLS"]["URL-target"]

    @property
    def url_image(self):
        """Docker registry url to processing image"""
        return self.data["Job"]["URLS"]["URL-image"]

    @property
    def environment(self):
        """Environment variables for the job"""
        return self.data["Job"]["Environment"]

    def claim(self, worker='anonymous'):
        if self.claimed:
            return
        try:
            self.api.claim_job(self.url_claim, worker)
            self.claimed = True
        except UClientError:
            raise

    def send_status(self, status, processing_time=None):
        self.api.update_status(
            self.url_status, status, processing_time=processing_time)

    def send_output(self, output):
        self.api.update_output(self.url_output, output)
