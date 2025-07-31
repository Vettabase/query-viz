#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/start.sh"
  exit 2
fi

# create the network manually to give it an arbitrary name
docker network create --driver=bridge qv 2> /dev/null

if [ -n "$COMPOSE_PROFILES" ]; then
    COMPOSE_PROFILES=default
fi

docker-compose --project-directory docker -f docker/docker-compose.yml up -d --build
