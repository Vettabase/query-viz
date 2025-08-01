#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/start.sh"
  exit 2
fi

# Make sure that all containers are stopped.
# Pull from git.
# Run the services in the "test" profile. This will run the tests.
# Show the stdout of the stopped qv-test container.
# Finally, stop all services that are still running.

COMPOSE_PROFILES=full docker/stop.sh

git pull

docker network create --driver=bridge qv 2> /dev/null
COMPOSE_PROFILES=test \
    docker-compose --project-directory docker -f docker/docker-compose.yml up -d --build
sleep 2
docker logs qv-test

COMPOSE_PROFILES=full docker/stop.sh
