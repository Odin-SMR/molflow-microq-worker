#!/bin/bash -x

set -e

sudo apt-get update -qq -y
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade
sudo apt-get -y -qq install wget curl --no-install-recommends
