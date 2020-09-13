#!/bin/sh

/usr/local/bin/initialize_cycling_data_db --delete-existing /run/secrets/production.ini

/usr/local/bin/pserve /run/secrets/production.ini
