#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/start.sh"
  exit 2
fi

docker-compose --project-directory docker -f docker/docker-compose.yml up -d --build
