from debian:jessie
run apt-get update && apt-get install -y \
    python-dev \
    python-pip \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

run pip install ConcurrentLogHandler==0.9.1
run pip install requests==2.11.1

copy src/ /app/
run cd /app && python setup.py develop

entrypoint ["uworker"]
