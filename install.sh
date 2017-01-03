#!/bin/bash

# Install uworker in a virtual env

set -e

command -v virtualenv >/dev/null 2>&1 || \
    { echo >&2 "Could not find virtualenv, install with 'pip install virtualenv'."; exit 1; }
virtualenv env
source env/bin/activate
pip install -r requirements.txt
cd src && python setup.py develop
deactivate
