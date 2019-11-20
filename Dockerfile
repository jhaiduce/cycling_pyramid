FROM python:3.7.2-alpine
FROM node:8-alpine

WORKDIR /app

RUN apk add --update python3 py3-pip python3-dev build-base zlib-dev libjpeg-turbo-dev libpng-dev freetype-dev
RUN pip3 install --trusted-host pypi.python.org --upgrade pip
RUN pip3 install --trusted-host pypi.python.org Pillow numpy
RUN apk add libffi-dev mariadb-dev
RUN apk add lapack-dev
RUN apk add gfortran

COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt
COPY cycling_data /app/cycling_data
COPY setup.py /app
COPY pytest.ini /app
COPY MANIFEST.in /app
COPY CHANGES.txt /app
COPY README.md /app
RUN pip3 install --trusted-host pypi.python.org -e .
COPY pyramid_start.sh /app

VOLUME ["/var/db"]

EXPOSE 80

ENV NAME World

CMD ["/app/pyramid_start.sh"]
