#!/bin/bash

# Setup test environment by starting a local uservice and configuring the
# uworker to use that.

set -e

login_to_registry() {
    source /root/uworker.conf
    docker login ${UWORKER_REGISTRY_URL} \
           -u ${UWORKER_REGISTRY_USERNAME} -p ${UWORKER_REGISTRY_PASSWORD}
}

start_uservice() {
    cd /src && docker-compose -p uservice up -d
}

job_api_root() {
    echo "http://localhost:5000/rest_api"
}

create_uservice_test_user() {
    local username=$1
    local password=$2
    local url

    url="$(job_api_root)/admin/users"
    curl -H "Content-Type: application/json" -X POST \
         -u "admin:sqrrl" \
         -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
         "$url"
}

fix_uworker_conf() {
    local username=$1
    local password=$2
    local api_root

    api_root=$(job_api_root)

    sed -i -e "s@.*UWORKER_JOB_API_ROOT.*@export UWORKER_JOB_API_ROOT=${api_root}@" /root/uworker.conf
    sed -i -e "s/.*UWORKER_JOB_API_USERNAME.*/export UWORKER_JOB_API_USERNAME=${username}/" /root/uworker.conf
    sed -i -e "s/.*UWORKER_JOB_API_PASSWORD.*/export UWORKER_JOB_API_PASSWORD=${password}/" /root/uworker.conf    
}

fix_uworker_start_script() {
    sed -i -e "s/uworker/python /app/uworker/uworker.py/" /root/start_worker.sh
}

main() {
    local worker_username="worker1"
    local worker_password="sqrrl"
    login_to_registry
    start_uservice
    sleep 5
    create_uservice_test_user $worker_username $worker_password
    fix_uworker_conf $worker_username $worker_password
    service supervisor start
}

main
