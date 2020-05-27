FROM python:3.8

COPY requirements.txt /tmp/
RUN pip install -r/tmp/requirements.txt

COPY src/ /app/
WORKDIR /app

RUN cd /app && python setup.py develop

entrypoint ["uworker"]
