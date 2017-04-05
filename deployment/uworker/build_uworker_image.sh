#!/bin/bash

set -e

if [[ -z $OS_PASSWORD ]]; then
    source 'SNIC 2017_13-7-openrc_v3.sh'
    source 'packer_openstack_v3.sh'
fi
tar -zcvf microq.tar.gz ../../src

if [[ $1 == validate ]]; then
    packer validate -var-file=variables.json xenial.json
elif [[ $1 == test ]]; then
    packer build -var-file=variables.json -only=null xenial.json
elif [[ $1 == local ]]; then
    packer build -var-file=variables.json -only="virtualbox-iso" xenial.json
else
    packer build -var-file=variables.json -only=openstack xenial.json
fi
