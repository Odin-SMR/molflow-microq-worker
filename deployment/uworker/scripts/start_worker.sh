#!/bin/bash
export HOSTNAME=$(hostname)
source uworker.conf
docker login -u ${DOCKERHUB_USERNAME} -p ${DOCKERHUB_TOKEN}
PYTHONPATH=/app python3 /app/uworker/uworker.py --no-command
