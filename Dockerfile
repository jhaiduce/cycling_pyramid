FROM python:3.8.6-slim-buster

WORKDIR /app

RUN apt-get update
RUN apt-get -y install python-numpy python-mysqldb python-scipy python-pandas python-shapely npm git libmariadb-dev python-cffi python-matplotlib libffi-dev libcap2-bin

COPY requirements.txt /app
RUN pip3 install --trusted-host pypi.python.org --upgrade pip
RUN pip3 install -r /app/requirements.txt
COPY cycling_data /app/cycling_data
COPY setup.py /app
COPY pytest.ini /app
COPY MANIFEST.in /app
COPY CHANGES.txt /app
COPY README.md /app
RUN pip3 install --trusted-host pypi.python.org -e .

COPY pyramid_start.sh /app
COPY pyramid_cold_start.sh /app
COPY celery_healthcheck.py /app

EXPOSE 80

ENV NAME World

RUN groupadd --system appuser && \
    useradd --system --no-create-home -s /bin/sh -g appuser appuser

RUN setcap CAP_NET_BIND_SERVICE=+eip /usr/local/bin/python3.8

USER appuser

HEALTHCHECK CMD curl --fail http://localhost/ || exit 1

CMD ["/app/pyramid_start.sh"]
