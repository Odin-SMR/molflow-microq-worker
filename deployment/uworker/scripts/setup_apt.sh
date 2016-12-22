#!/bin/bash -x

set -e

# Use closer apt-mirrons
cat <<EOF | sudo tee /etc/apt/sources.list
deb http://mirrors.telianet.dk/ubuntu/ xenial main restricted universe multiverse
deb http://mirrors.telianet.dk/ubuntu/ xenial-updates main restricted universe multiverse
deb http://mirrors.telianet.dk/ubuntu/ xenial-backports main restricted universe multiverse
deb http://mirrors.telianet.dk/ubuntu/ xenial-security main restricted universe multiverse
EOF
