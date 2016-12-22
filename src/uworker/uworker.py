"""
Worker that performs jobs provided by a uservice api.

 ---------          --------                      --------------
 |Job API| <------> |Worker| - <Command> <------> |External API|
 ---------          --------                      --------------

The worker can run on the host or in a docker image.
In both cases the root url and credentials to the job api must be available
as environment variables.

Worker on host
--------------

The worker asks the job api for a job from any project (the job api prioritize
the projects).
The jobs must include an url to a docker image that the worker pulls.

Worker in docker image
----------------------

The worker asks the job api for a job from a certain project.
The project and the command that should be executed for all the jobs in the
project are provided to the docker container as environment variables.
"""

import os
import errno
from sys import exit
import signal
import subprocess
import argparse
from io import BytesIO
from time import sleep, time
from datetime import datetime
from threading import Thread, Lock

from uclient.uclient import UClient, UClientError, Job
from utils import docker_util
from utils.logs import get_logger
from utils.defs import JOB_STATES

GENERAL_CONFIG = {
    'api_root': ('UWORKER_JOB_API_ROOT', True),
    'api_username': ('UWORKER_JOB_API_USERNAME', True),
    'api_password': ('UWORKER_JOB_API_PASSWORD', True),
    'external_username': ('UWORKER_EXTERNAL_API_USERNAME', False),
    'external_password': ('UWORKER_EXTERNAL_API_PASSWORD', False)
}

IN_DOCKER_CONFIG = {
    'container_id': ('HOSTNAME', True),
    # Set by start script
    'hostname': ('UWORKER_HOSTNAME', True),
    # Set by Dockerfile
    'job_command': ('UWORKER_JOB_CMD', True),
    'job_type': ('UWORKER_JOB_TYPE', True),
    'job_timeout': ('UWORKER_JOB_TIMEOUT', False),
    'api_project': ('UWORKER_JOB_API_PROJECT', True),
}

ON_HOST_CONFIG = {
    'hostname': ('HOSTNAME', True)
}


def get_config(in_docker):
    """Create config dict from environment variables"""
    conf = GENERAL_CONFIG.copy()
    if in_docker:
        conf.update(IN_DOCKER_CONFIG)
    else:
        conf.update(ON_HOST_CONFIG)
    loaded_conf = {}
    for key, (env, required) in conf.items():
        if required:
            loaded_conf[key] = os.environ[env]
        else:
            loaded_conf[key] = os.environ.get(env)
    return loaded_conf


class UWorkerError(Exception):
    pass


class UWorker(object):
    """
    Worker flow
    -----------

    1. Ask job api for jobs to perform.
    2. Claim a job.
    3. Run job command/image with source and target url as arguments.
    4. Continuously send output from command/image to api.
    5. When command/image exits, send exit code to api and set job status to
       finished if code == 0, else set status to failed.

    The job command
    ---------------

    The worker will call the job command with an url that should
    return input data and an url that the command should send the
    results to.
    The worker can also provide the command with credentials to the
    target url if needed.

    >>> /path/to/command INPUT_URL [TARGET_URL USERNAME PASSWORD]]

    The command should only exit successfully if the result was accepted
    by the target api. The worker can then set the status of the job to
    failed or finished by looking at the exit code of the command.
    """
    # Sleep this many seconds when no jobs are available
    IDLE_SLEEP = 1
    # Sleep this many seconds if something unexpected goes wrong
    ERROR_SLEEP = 10

    def __init__(self, start_service=False):
        self.in_docker = docker_util.in_docker()
        try:
            config = get_config(self.in_docker)
        except KeyError as e:
            raise UWorkerError('Missing config value: %s' % e)
        self.name = '{class_name}_{host}'.format(
            class_name=self.__class__.__name__,
            host=config['hostname'])
        self.log = get_logger(
            self.name, to_file=start_service, to_stdout=True)
        self.job_count = 0
        self.log_config(config)
        self.project = self.job_type = self.job_timeout = self.cmd = None

        if self.in_docker:
            self.name += '_' + config['container_id']
            self.project = config['api_project']
            self.cmd = config['job_command']
            self.job_type = config['job_type']
            self.job_timeout = config['job_timeout']
            if self.job_timeout:
                self.job_timeout = int(self.job_timeout)

        self.api = UClient(config['api_root'],
                           username=config['api_username'],
                           password=config['api_password'],
                           time_between_retries=self.ERROR_SLEEP)
        self.external_auth = (config['external_username'],
                              config['external_password'])
        if start_service:
            self.alive = True
            signal.signal(signal.SIGINT, self.stop)
            signal.signal(signal.SIGTERM, self.stop)
            self.run()

    def log_config(self, config):
        self.log.info('Loaded config:')
        for k, v in sorted(config.items()):
            self.log.info('%s = %s' % (k, v))

    def run(self, only_once=False):
        self.running = True
        while self.alive:
            if only_once:
                self.alive = False
            try:
                job = Job.fetch(
                    self.api, job_type=self.job_type, project=self.project)
                if not job:
                    sleep(self.IDLE_SLEEP)
                elif self.claim_job(job):
                    job.send_status(JOB_STATES.started)
                    exit_code, processing_time = self.do_job(
                        job.url_source, job.url_target, job.url_output,
                        job.url_image, job.environment)
                    if exit_code == 0:
                        job.send_status(JOB_STATES.finished, processing_time)
                    else:
                        job.send_status(JOB_STATES.failed, processing_time)
                    self.job_count += 1
            except Exception as e:
                self.log.exception('Unhandled exception: %s' % e)
                sleep(self.ERROR_SLEEP)
        self.running = False

    def stop(self, signal, frame):
        # TODO: Should kill job command and unclaim current job
        self.alive = False

    def claim_job(self, job, nr_trials=5):
        for _ in range(nr_trials):
            try:
                job.claim(worker=self.name)
                return True
            except UClientError as e:
                if e.status_code == 409:
                    return False
                self.log.error('Failed job claim: %s' % e)
                sleep(self.ERROR_SLEEP)
        return False

    def do_job(self, url_source, url_target=None, url_output=None,
               url_image=None, environment=None):
        args = [url_source]
        if url_target:
            args.append(url_target)
            args.extend(cred for cred in self.external_auth if cred)

        def output_callback(output):
            if url_output:
                try:
                    # TODO: Limit size of output that can be sent
                    self.api.update_output(url_output, output)
                except:
                    self.log.exception(
                        'Exception when sending output to job api:')

        self.log.info('Starting job: %s' % args)
        # TODO: Add support for letting a job override the configured timeout
        if url_image:
            assert not self.in_docker
            executor = DockerExecutor(
                'Job', url_image, self.log, environment=environment)
        else:
            assert self.in_docker
            executor = CommandExecutor('Job', self.cmd, self.log)

        exit_code, processing_time = executor.execute(
            args, output_callback, timeout=self.job_timeout)
        return exit_code, processing_time


class ExecutorError(Exception):
    pass


class CommandExecutor(object):
    """Class for execution of commands.

    Example usage:

    >>> def callback_function(message):
    >>>     print(message)
    >>> c = CommandExecutor('Pack dir', 'tar -zcvf', log)
    >>> c.execute(['packed.tar.gz', '/pack/this/dir'], callback_function)
    """
    def __init__(self, name, cmd, log):
        if isinstance(cmd, basestring):
            cmd = cmd.split()
        self.cmd = cmd
        self.process_name = name
        self.log = log
        self.output_lock = Lock()

    def execute(self, command_args, output_callback, timeout=None,
                kill_after=5):
        """
        Execute the command with args and monitor the progress.

        Args:
          commandd_args (list): List of arguments to provide to the command.
          output_callback (function): Call this function with stdout/stderr
            output from the command as argument.
          timeout (int): Send TERM to the command if it has not finished
            after this many seconds.
          kill_after (int): Also send KILL (9) if it still is
            alive this many seconds after TERM was sent.
        """
        cmd = self.cmd + command_args
        if timeout:
            if not isinstance(timeout, int) or timeout <= 0:
                raise ExecutorError(
                    'timeout must be a positive integer, timeout=%r' % timeout)
            cmd = ['timeout', '--kill-after=%d' % kill_after,
                   str(int(timeout))] + cmd
        start_time = time()
        popen = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        self.log.info('{} process started with pid {}: {}'.format(
            self.process_name, popen.pid, cmd))

        output = BytesIO()
        self._handle_output(popen, output, output_callback)
        exit_code, killed = self._wait_for_exit(popen)
        processing_time = time() - start_time

        if timeout and killed:
            msg = ('Killed {} process after timeout of {} seconds'
                   '').format(self.process_name, timeout)
            self._write_output('executor', msg + '\n', output)
            self.log.warning(msg)

        msg = '{} process exited with code {}'.format(
            self.process_name, exit_code)
        self._write_output('executor', msg + '\n', output)
        output_callback(output.getvalue())
        if exit_code != 0:
            self.log.warning(msg)
        else:
            self.log.info(msg)
        return exit_code, processing_time

    def _handle_output(self, popen, out_buffer, out_callback):
        """Start threads that feed the stdout/stderr streams from the
        subprocess to the callback function.
        """
        stdout_lines = iter(popen.stdout.readline, "")
        stderr_lines = iter(popen.stderr.readline, "")

        t_stdout = Thread(target=self._read_lines, args=(
            'stdout', stdout_lines, out_buffer, out_callback))
        t_stderr = Thread(target=self._read_lines, args=(
            'stderr', stderr_lines, out_buffer, out_callback))
        t_stdout.start()
        t_stderr.start()
        return t_stdout, t_stderr

    def _read_lines(self, stream_name, lines, out_buffer, out_callback):
        """Read stream from subprocess and feed to log and callback function"""
        last_callback = 0
        callback_interval = 5
        for line in lines:
            with self.output_lock:
                self._write_output(stream_name, line, out_buffer)
                if time() - last_callback > callback_interval:
                    out_callback(out_buffer.getvalue())
                    last_callback = time()
            if line.strip():
                self.log.info(
                    '{process_name} process {stream}: {message}'.format(
                        process_name=self.process_name, stream=stream_name,
                        message=line.strip()))

    def _wait_for_exit(self, popen):
        """Wait for the subprocess to exit.

        Args:
          popen (Popen): The subprocess object.
        Return:
          (int, bool): Subprocess exit code, True if killed because of timeout.
        """
        exit_code = popen.poll()
        while exit_code is None:
            sleep(1)
            exit_code = popen.poll()

        killed = exit_code in (124, 128+9)

        if docker_util.in_docker():
            self._reap_children(popen.pid)

        for stream_name, stream in (('stdout', popen.stdout),
                                    ('stderr', popen.stderr)):
            try:
                stream.close()
            except Exception as e:
                self.log.warning(
                    'Could not close command stream {}: <{}> {}'.format(
                        stream_name, e.__class__.__name__, e))

        return exit_code, killed

    def _reap_children(self, pid):
        """Docker does not reap orphaned children, see:
        https://blog.phusion.nl/2015/01/20/docker-and-the-pid-1-zombie-reaping-problem/
        """
        try:
            this_pid, status = os.waitpid(-1, 0)
            self.log.info('Reaped child %s, exit code: %s' % (
                this_pid, status))
            while this_pid != pid:
                this_pid, status = os.waitpid(-1, 0)
                self.log.info('Reaped child %s, exit code: %s' % (
                    this_pid, status))
        except OSError as e:
            if e.errno in (errno.ECHILD, errno.ESRCH):
                return
            raise

    @staticmethod
    def _write_output(stream_name, msg, output):
        output.write('%s - %s: %s' % (
            datetime.utcnow().isoformat(), stream_name.upper(), msg))


class DockerExecutor(CommandExecutor):
    """Class for execution of commands wrapped in a docker image.
    The entrypoint of the image will be called with the provided arguments.

    Example usage:

    >>> def callback_function(message):
    >>>     print(message)
    >>> c = DockerExecutor('Command in docker',
                           'my.registry.com/imagename:tag', log)
    >>> c.execute(['argument1', 'arg2'], callback_function)

    The image is pulled from the registyr if it does not exist on the host.
    """

    def __init__(self, name, image_url, log, auto_remove=True,
                 environment=None, network='host'):
        environment = environment or {}
        self.image_url = image_url
        env = sum(
            [['-e', '"%s=%s"' % (k, v)] for k, v in environment.items()], [])

        cmd = ['docker', 'run', '-i']
        if auto_remove:
            cmd.append('--rm')
        if network:
            cmd.append('--network=%s' % network)
        cmd += env + [image_url]
        super(DockerExecutor, self).__init__(name, cmd, log)

    def execute(self, command_args, output_callback, timeout=None):
        pull_exit_code = self.pull_image(output_callback)
        if pull_exit_code != 0:
            return pull_exit_code, 0
        return super(DockerExecutor, self).execute(
            command_args, output_callback, timeout=timeout)

    def pull_image(self, output_callback):
        if not self.image_exists():
            executor = CommandExecutor(
                'Pull image', ['docker', 'pull'], self.log)
            code, _ = executor.execute([self.image_url], output_callback)
            return code
        return 0

    def image_exists(self):
        executor = CommandExecutor(
            'Image exists', ['docker', 'images', '-q'], self.log)

        def output_callback(message):
            if 'EXECUTOR' in message:
                return
            output_callback.exists = bool(message)
        output_callback.exists = False

        code, _ = executor.execute([self.image_url], output_callback)
        if code != 0:
            raise ExecutorError(
                'Could not check if docker image %s exists, exit code: %s' % (
                    self.image_url, code))
        return output_callback.exists


def get_argparser():
    parser = argparse.ArgumentParser(
        description='Start UWorker service if no input url is provided.')
    parser.add_argument(
        'INPUT_DATA_URL', nargs='?',
        help='If provided, run job command on this input url and exit.')
    return parser


def main(args=None):
    parser = get_argparser()
    args = parser.parse_args(args)
    if args.INPUT_DATA_URL:
        if not docker_util.in_docker():
            # TODO: Add support for giving a processing image url via command
            #       line.
            print('Cannot run job outside of docker')
            return 1
        worker = UWorker()
        return worker.do_job(args.INPUT_DATA_URL)
    else:
        print('Spawning worker')
        UWorker(start_service=True)

if __name__ == '__main__':
    exit(main())
