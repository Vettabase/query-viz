#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/rebuild.sh"
  exit 2
fi

docker-compose -f docker/docker-compose.yml down
