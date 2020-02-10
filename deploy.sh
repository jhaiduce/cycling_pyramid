docker-compose build && \
    docker-compose push && \
    docker stack deploy -c docker-compose.yml cycling_stack && \
    docker service update --image jhaiduce/cycling-pyramid cycling_stack_cycling_web && \
    docker service update --image jhaiduce/cycling-pyramid cycling_stack_worker
