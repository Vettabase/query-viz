# query-viz
A tool to generate real-time charts using GNU Plot.


## Configuration (with Docker Compose)

Create the configuration file:

```
cp config.yaml.template config.yaml
```

Then, edit the configuration file. The file contains comments that explain the meaning
of the various settings.

Now you can start the containers with our helper scripts
(note that Docker Compose is required):

```
COMPOSE_PROFILES=default docker/rebuild.sh
```

To also create a test MariaDB container:

```
COMPOSE_PROFILES=default,mariadb docker/rebuild.sh
```

Now Query Viz should start to collect data and compose charts.
To view the charts, point your browser to:

http://localhost:8080


## Usage Notes

If you modify the configuration file, you should restart Query-Viz.
In the Docker environment, you should recreate the containers.


## Copyright and License

Copyright: Vettabase 2025

License: AGPLv3.
