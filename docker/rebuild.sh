#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/rebuild.sh"
  exit 2
fi

docker/stop.sh
git pull || exit 1
docker/start.sh
