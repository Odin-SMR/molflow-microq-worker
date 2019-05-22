#!/bin/bash
export HOSTNAME=$(hostname)
source uworker.conf
docker login ${UWORKER_REGISTRY_URL} \
       -u ${UWORKER_REGISTRY_USERNAME} -p ${UWORKER_REGISTRY_PASSWORD}
docker login -u ${DOCKERHUB_USERNAME} -p ${DOCKERHUB_PASSWORD}
PYTHONPATH=/app python3 /app/uworker/uworker.py --no-command
