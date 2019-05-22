#!/bin/bash -x

set -e

sudo apt-get install -y -qq python3-dev python3-pip --no-install-recommends

sudo pip3 install --upgrade pip
sudo pip3 install setuptools

tar xf /tmp/microq.tar.gz
rm /tmp/microq.tar.gz
sudo mv src /app

# TODO: Install in virtual env
sudo pip3 install -r /tmp/uworker-requirements.txt

# TODO: Do not run as root
sudo mv /tmp/start_worker.sh /root/start_worker.sh
sudo mv /tmp/uworker.conf /root/uworker.conf
sudo chown root:root /root/start_worker.sh
sudo chown root:root /root/uworker.conf
sudo chmod u+x /root/start_worker.sh
