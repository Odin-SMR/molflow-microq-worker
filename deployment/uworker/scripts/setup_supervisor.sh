#!/bin/bash -x

set -e

sudo apt-get install -y -qq supervisor

cat >"uworker.conf" <<EOF
[program:uworker]
command=/root/start_worker.sh
directory=/root
redirect_stderr=true
autostart=true
autorestart=true 
priority=10 
EOF

sudo mv uworker.conf /etc/supervisor/conf.d/uworker.conf

sudo systemctl enable supervisor
