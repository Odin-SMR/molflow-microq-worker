#!/bin/bash
export HOSTNAME=$(hostname)
source uworker.conf
docker login ${UWORKER_REGISTRY_URL} \
       -u ${UWORKER_REGISTRY_USERNAME} -p ${UWORKER_REGISTRY_PASSWORD}
PYTHONPATH=/app python /app/uworker/uworker.py
