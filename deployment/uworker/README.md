
# Build uworker cloud images

## Packer

The images are built with packer: https://www.packer.io/

The installation of packer is very simple, it is distributed as a binary
package.

https://www.packer.io/docs/installation.html

Tested with version `0.10.2`.

## Config files

There are two config files that must be provided. The openstack config
`c2016005-openrc.sh` is hard coded for now and was fetched from the smog
dashboard:

    Access & security >> API Access >> Download OpenStack RC File

### Worker config

The worker needs to know the job service root url and credentials.
The job service users can be created by the job service admin user,
see README.md in the root of this repository.
The worker must also have access to a docker registry.

Put these config variables in a file:

    export UWORKER_JOB_API_ROOT=http://example.com/uservice/api/root
    export UWORKER_JOB_API_USERNAME=<uservice username>
    export UWORKER_JOB_API_PASSWORD=<uservice password>
    export UWORKER_REGISTRY_URL=https://example.com/docker/registry
    export UWORKER_REGISTRY_USERNAME=<docker registry username>
    export UWORKER_REGISTRY_PASSWORD=<docker registry password>

### Packer config

The variables must be provided in a file with the name `variables.json`
located in the same directory as the build script (`build_uworker_image.sh`).

Required config variables:

* `openstack_free_floating_ip`: An available floating ip.
* `uworker_config_file`: Path to the worker config file.

When developing the provisioning scripts a test host can be used
(more info [below](#development)):

* `test_host`: The host name or the ip of the test host.
* `test_ssh_key`: The ssh private key to the test host.

Example contents of `variables.json`:

    {
        "openstack_free_floating_ip": "130.238.29.214",
        "uworker_config_file": "/path/to/uworker.conf",
        "test_host": "130.238.29.14",
        "test_ssh_key": "/home/<username>/.ssh/cloud.key"
    }

## Build image

Now you should be setup to build the uworker smog image:

    ./build_uworker_image.sh

The first time this is run it will ask for your smog credentials.
Smog can be a bit unstable so do not be surprised if it does not work on the
first trial.

The saving of the image can take a long time, normal is 10-20 minutes,
but somtetimes several hours.

## Development of packer build scripts

Validate the packer template (`xenial.json`):

    ./build_uworker_image.sh validate

Test the provisioning scripts on a manually booted test instance:

    ./build_uworker_image.sh test

This makes it much faster to iterate during development. The provisioning
scripts are directly run on the test instance instead of booting
a new instance every time.

## Development of uworker

Build virtualbox image for running the worker in a vm on your machine:

    ./build_uworker_image.sh local

The build should result in an image file named `packer_virtualbox-iso_virtualbox.box`
in the same directory as the build script. The image can be used with vagrant.

### Install vagrant and virtualbox

Install vagrant by downloading package from:

    https://www.vagrantup.com/downloads.html

Tested and working with vagrant version `1.8.6` and virtualbox version `5.0.24`.

Install plugins:

    vagrant plugin install vagrant-vbguest

### Start vm and setup test environment

Run these commands in the same directory as the build script:

    vagrant box add packer_virtualbox-iso_virtualbox.box --name molflow/uworker-xenial
    vagrant up

Now you should have a virtualbox vm running with the src directory of this repo
mounted at /app and the root of this repo mounted at /src in the vm.

Jump into the vm and setup the test environment:

    host$ vagrant ssh
    vm$ cd /src/deployment/uworker
    vm$ sudo su root
    vm# ./setup_test_env.sh

This will start a uservice docker container in the vm and a uworker that
uses that uservice. The local code on your machine is used for both services.

It is now possible to add projects and jobs to the local uservice that the
local uworker will execute via docker images.
