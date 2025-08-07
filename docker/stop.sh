#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/start.sh"
  exit 2
fi

COMPOSE_PROFILES=full docker-compose -f docker/docker-compose.yml down && \
    docker network rm qv 2> /dev/null
