docker-compose build && \
    docker-compose push && \
    docker stack deploy -c docker-compose.yml cycling_stack && \
    docker service update --image jhaiduce/cycling-pyramid-web cycling_stack_cycling_web && \
    docker service update --image jhaiduce/cycling-pyramid-worker cycling_stack_worker
