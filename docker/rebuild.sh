#!/bin/bash

if [ ! -d "docker" ]; then
  echo "This script should be called by the parent directory, in this way:"
  echo "docker/rebuild.sh"
  exit 2
fi

docker/stop.sh

if [ ! -z "$BRANCH" ]; then
    git checkout $BRANCH
    r=$?
    if [ $r != "0" ];
    then
        echo "Could not select branch $BRANCH"
        echo "ABORTING"
        exit $r
    fi
fi

git pull || exit 1
git log -1 --format="%H" -- docker/web > docker/web/AUTO_VERSION

docker/start.sh
