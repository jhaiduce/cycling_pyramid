#!/bin/sh

/usr/bin/initialize_cycling_data_db --delete-existing /run/secrets/production.ini

/usr/bin/pserve /run/secrets/production.ini
