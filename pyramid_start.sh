#!/bin/sh

/usr/bin/initialize_cycling_data_db /run/secrets/production.ini

if [ $? -ne 0 ]; then
    exit $?;
fi

/usr/bin/pserve /run/secrets/production.ini

if [ $? -ne 0 ]; then
    exit $?;
fi
