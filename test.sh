export VENV=`pwd`/../venv

sudo docker kill cycling_test_cycling_web
sudo docker kill cycling_test_worker
sudo docker kill ci_sut_1

declare -a secret_files=("integration_test.ini" "mysql_root_password_test" "ca.pem")

for file in "${arr[@]}"
do
    chcon -t svirt_sandbox_file_t "$file"
done

$VENV/bin/pytest -q && \
    sudo docker-compose -f docker-compose.test.yml -p ci build && \
    sudo docker-compose -f docker-compose.test.yml -p ci up -d && \
    sudo docker logs -f ci_sut_1
