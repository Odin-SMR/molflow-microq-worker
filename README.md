# Microq service worker

The worker is an application that processes jobs provided by the microq api.

The worker needs these environment variables to be able to communicate with the
api:

    export UWORKER_JOB_API_ROOT=https://example.com/rest_api
    export UWORKER_JOB_API_USERNAME=<username>
    export UWORKER_JOB_API_PASSWORD=<password>

The environment could for example be provided by adding the variables to a
config file and then source that file before starting the worker:

    source config_file.conf

## Run worker manually for a certain project

This is the default mode when the worker is started without arguments:

    uworker

Install the worker by calling the install script:

    ./install.sh

This will install the worker and its dependencies in a virtual environment.
The worker can then be started like this:

    # Load environment variables
    source config_file.conf
    # Activate the virtual env
    source env/bin/activate
    # Start the worker
    uworker

The worker must be provided with a project name and a command to run for the
jobs that belong to that project. Add these environment variables to the config
file:

    export UWORKER_JOB_API_PROJECT=<project_name>
    export UWORKER_JOB_CMD=<job command to execute>

The job command must be available on the computer that the worker is running on.

## Run in multiple projects mode

In this mode the worker asks the microq api for jobs from any project:

    uworker --no-command

The projects are prioritized by the api. A docker image url for each job is
also provided by the api. The image contains the processing command and the
worker will pull that docker image and process the job via that image.

## The processing command

The worker provides two arguments to the processing command:

    processing_command input_data_url result_data_url

The input url should be used to get input data to the processing algorithm
and the result url should be used to store the results of the processing.

How this is done is up to the processing application. The urls could point
to a rest api or they could be file paths if the data should be stored on
the file system or on a cloud.

### Implementation details

#### Exit code

The command should only exit with an error code if an unexpected error occurs
in the processing. If an error that is known occurs, that information should be
sent as a processing result to the target url.

An example of an error that should result in an exit code != 0 is if the
storing of the result data fails.

#### Stdout/stderr

Output from the processing command is stored by the worker in the
microq service and can be inspected in the microq web interface.
Make sure that the output is useful and not too verbose.
