docker build -t jhaiduce/cycling-pyramid-base -f Dockerfile.base . && \
    docker build -t jhaiduce/cycling-pyramid-web -f Dockerfile.web . && \
    docker build -t jhaiduce/cycling-pyramid-worker -f Dockerfile.worker . && \
    docker push jhaiduce/cycling-pyramid-base && \
    docker push jhaiduce/cycling-pyramid-worker && \
    docker push jhaiduce/cycling-pyramid-web && \
    docker stack deploy -c docker-compose.yml cycling_stack && \
    docker service update --image jhaiduce/cycling-pyramid-web cycling_stack_cycling_web && \
    docker service update --image jhaiduce/cycling-pyramid-worker cycling_stack_worker
