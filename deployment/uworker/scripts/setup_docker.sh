#!/bin/bash -x

set -e

# Ensure that APT works with the https method, and that CA certificates
# are installed.
sudo apt-get install -y -qq apt-transport-https ca-certificates

# Add new GPG key
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

# Update apt sources
echo deb https://apt.dockerproject.org/repo ubuntu-xenial main | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update -qq -y

# Purge old if exists
sudo apt-get purge -y lxc-docker

# linux extra allows us to use the aufs storage driver
sudo apt-get install -y -qq linux-image-extra-$(uname -r) linux-image-extra-virtual

# Install docker engine
sudo apt-get install -y -qq docker-engine
sudo systemctl enable docker

sudo apt-get install -y -qq docker-compose
