#!/bin/bash

# Install uworker in a virtual env

set -e

command -v virtualenv >/dev/null 2>&1 || \
    { echo >&2 "Could not find virtualenv, install with 'pip install virtualenv'."; exit 1; }
virtualenv -p python3 env
source env/bin/activate
pip3 install -r requirements.txt
cd src && python3 setup.py develop
deactivate
