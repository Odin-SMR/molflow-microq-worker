#!/bin/bash -x

set -e

# Purge old if exists
sudo apt-get purge -y docker docker-engine docker.io containerd runc
# Ensure that APT works with the https method, and that CA certificates
# are installed.
sudo apt-get update
sudo apt-get install -y -qq apt-transport-https ca-certificates curl gnupg-agent software-properties-common

# Add new GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Update apt sources
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update -qq -y


# Install docker-ce
sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
