FROM python:3.7.2-alpine
FROM node:8-alpine

WORKDIR /app

RUN apk add --update python3 py3-pip python3-dev build-base zlib-dev libjpeg-turbo-dev libpng-dev freetype-dev
RUN pip3 install --trusted-host pypi.python.org --upgrade pip
RUN pip3 install --trusted-host pypi.python.org Pillow numpy

COPY . /app
RUN pip3 install --trusted-host pypi.python.org -e .

VOLUME ["/var/db"]

EXPOSE 80

ENV NAME World

CMD ["/usr/bin/pserve","/app/production.ini"]
