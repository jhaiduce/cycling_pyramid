#!/bin/bash

export VENV=`pwd`/../venv

sudo docker kill cycling_test_cycling_web
sudo docker kill cycling_test_worker
sudo docker kill ci_sut_1

secret_files=("integration_test.ini" "mysql_root_password_test" "ca.pem" "server-cert.pem" "server-key.pem" "storage_key.keyfile" "mysql-config-cycling.cnf")

for file in "${secret_files[@]}"
do
    chcon -t svirt_sandbox_file_t "$file"
done

set -e

# Run unit tests
$VENV/bin/pytest -q

# Run migration tests
$VENV/bin/pytest -q cycling_data/migration_tests.py

# Build images
sudo docker-compose -f docker-compose.test_secrets.yml -f docker-compose.db.yml -f docker-compose.test.yml -p ci build

# Migrate database
sudo docker-compose -f docker-compose.test_secrets.yml -f docker-compose.db.yml -f docker-compose.migrate.yml -p ci up -d

sudo docker wait ci_migration_1

# Print migration logs
sudo docker logs ci_migration_1

# Run tests
sudo docker-compose -f docker-compose.test_secrets.yml -f docker-compose.db.yml -f docker-compose.test.yml -p ci up -d

# Print test logs
sudo docker logs -f ci_sut_1
