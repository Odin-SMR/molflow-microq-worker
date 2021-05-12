#!/bin/bash

set -e

if [[ -z $OS_PASSWORD ]]; then
    source 'openrc.sh'
    source 'packer_openstack_v3.sh'
fi
tar -zcvf microq.tar.gz ../../src

if [[ $1 == validate ]]; then
    ../dependencies/packer validate -var-file=variables.json bionic.json
elif [[ $1 == test ]]; then
    ../dependencies/packer build -var-file=variables.json -only=null bionic.json
elif [[ $1 == local ]]; then
    packer build -var-file=variables.json -only="virtualbox-iso" bionic.json
else
    ../dependencies/packer build -var-file=variables.json -only=openstack bionic.json
fi
