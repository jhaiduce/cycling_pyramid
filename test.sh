export VENV=`pwd`/../venv

sudo docker kill cycling_test_cycling_web
sudo docker kill ci_sut_1

set -e

# Run unit tests
$VENV/bin/pytest -q

# Run migration tests
$VENV/bin/pytest -q cycling_data/migration_tests.py

# Build images
sudo docker-compose -f docker-compose.test.yml -p ci build

# Run tests
sudo docker-compose -f docker-compose.test.yml -p ci up -d

# Print test logs
sudo docker logs -f ci_sut_1
