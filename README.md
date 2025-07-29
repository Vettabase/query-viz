# query-viz
A tool to generate real-time charts using GNU Plot.


## Configuration

Create the configuration file:

```
cp config.yaml.template config.yaml
```

Then, edit the configuration file. The file contains comments that explain the meaning
of the various settings.

Now you can start the containers with Docker Compose:

```
cd docker
docker-compose up -d
```

Now Query Viz should start to collect data and compose charts.
To view the charts, point your browser to:

http://localhost:8080


## Copyright and License

Copyright: Vettabase 2025

License: AGPLv3.
