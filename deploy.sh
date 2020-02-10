docker build -t jhaiduce/cycling-pyramid -f Dockerfile . && \
    docker push jhaiduce/cycling-pyramid && \
    docker stack deploy -c docker-compose.yml cycling_stack && \
    docker service update --image jhaiduce/cycling-pyramid cycling_stack_cycling_web
