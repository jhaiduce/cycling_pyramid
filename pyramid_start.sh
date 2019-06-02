#!/bin/sh

if [ ! -f /var/db/cycling_data.sqlite ]; then
    /usr/bin/alembic -c /app/production.ini upgrade head
fi
/usr/bin/docker_secrets_to_ini

/usr/bin/pserve /app/production.ini
