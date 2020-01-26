FROM python:3.7.2-alpine
FROM node:8-alpine

WORKDIR /app

RUN apk add --update python3 py3-pip python3-dev build-base zlib-dev libjpeg-turbo-dev libpng-dev freetype-dev
RUN pip3 install --trusted-host pypi.python.org --upgrade pip
RUN pip3 install --trusted-host pypi.python.org Pillow numpy
RUN apk add libffi-dev mariadb-dev
RUN apk add lapack-dev
RUN apk add gfortran

RUN apk add build-base curl

# GEOS-3.6.0
RUN curl -so geos-3.6.0.tar.bz2 \
    http://download.osgeo.org/geos/geos-3.6.0.tar.bz2
RUN tar xjf geos-3.6.0.tar.bz2
RUN cd geos-3.6.0 && \
    ./configure --prefix=/usr \
      --disable-swig \
      --disable-static \
    && make install-strip
RUN cd .. && rm -rf geos-3.6.0*

RUN GEOS_CONFIG=/usr/bin/geos-config pip3 install shapely

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

EXPOSE 80

ENV NAME World

RUN addgroup --system appuser && \
    adduser --system -s /bin/sh --no-create-home appuser appuser

RUN apk add libcap

RUN setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python3.6

USER appuser

CMD ["/app/pyramid_start.sh"]
