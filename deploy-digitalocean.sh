#!/bin/bash

set -e

numworkers=1

DOTAGS=cycling

node_image=ubuntu-18-04-x64

host_prefix=cycling

stack_name=cycling_stack

node_size=s-2vcpu-2gb

sudo docker-compose -f docker-compose.yml build

sudo docker-compose -f docker-compose.yml push

if [ $(docker-machine ls -q|grep -c cycling-master) -eq "0" ]; then
  docker-machine create --driver digitalocean \
		 --digitalocean-size=$node_size \
		 --digitalocean-image $node_image \
		 --digitalocean-access-token $DOTOKEN \
		 --digitalocean-tags $DOTAGS \
		 $host_prefix-master
  master_ip=$(docker-machine ip $host_prefix-master)
  docker-machine ssh $host_prefix-master docker swarm init --advertise-addr $master_ip
else
  master_ip=$(docker-machine ip $host_prefix-master)
fi

docker-machine ssh $host_prefix-master docker node update --label-add db=true $host_prefix-master

for i in $(seq 1 $numworkers); do
    if [ $(docker-machine ls -q|grep -c $host_prefix-$i) -eq "0" ]; then
	docker-machine create --driver digitalocean \
		       --digitalocean-size $node_size \
		       --digitalocean-image $node_image \
		       --digitalocean-access-token $DOTOKEN \
		       --digitalocean-tags $DOTAGS \
		       $host_prefix-$i
    fi
done

join_token=$(docker-machine ssh $host_prefix-master docker swarm join-token -q worker)

for file in docker-compose.yml mysql-config-cycling.cnf mysql_production_password mysql_root_password pyramid_auth_secret cycling_admin_password production.ini storage_key.keyfile ca.pem server-key.pem server-cert.pem cycling_rabbitmq_password; do
    docker-machine scp $file $host_prefix-master:
done

docker-machine ssh $host_prefix-master mkdir -p nginx/ssl

for file in nginx/*.conf; do
    docker-machine scp $file $host_prefix-master:nginx
done

for file in nginx/dhparams.pem production_secrets/fullchain.pem production_secrets/privkey.pem; do
    docker-machine scp $file $host_prefix-master:nginx/ssl
done

function isSwarmNode(){
    host=$1
    if [ "$(docker-machine ssh $host docker info | grep Swarm | sed 's/ Swarm: //g')" == "active" ]; then
        swarm_node=1
    else
        swarm_node=0
    fi
}

for i in $(seq 1 $numworkers); do
    host=$host_prefix-$i
    isSwarmNode $host
    if [ $swarm_node == 1 ]; then
        echo "$host_prefix-$i is already a member of the swarm"
    fi
    if [ $swarm_node == 0 ]; then
    echo "Joining node $i to swarm"
	docker-machine ssh $host \
		       docker swarm join --token $join_token $master_ip:2377
    fi
done

docker-machine ssh $host_prefix-master docker stack deploy -c docker-compose.yml $stack_name

# Update images for running services
docker-machine ssh $host_prefix-master docker service update --image jhaiduce/cycling-pyramid ${stack_name}_worker
docker-machine ssh $host_prefix-master docker service update --image jhaiduce/cycling-pyramid ${stack_name}_cycling_web