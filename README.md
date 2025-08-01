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

If you only want to generate GNU Plot charts and don't need a ready-made
interface, you don't need the `qv-web` container.

If you modify the configuration file, you should restart Query-Viz.
In the Docker environment, you should recreate the containers.

To only start the containers if they're not already up:

```
COMPOSE_PROFILES=default docker/start.sh
```

To destroy the containers and volumes:

```
COMPOSE_PROFILES=default docker/stop.sh
```


## Directory Tree

Query-Viz' directory structure is the following:

```
query-viz/
├── qv.py                      # Main entry point
├── config.yaml.template       # Configuration file template
├── config.yaml                # Configuration file (you should create it!)
├── template.plt               # GNU Plot template
├── requirements.txt           # Python dependencies (production)
├── requirements-test.txt      # Python dependencies (tests)
├── pytest.ini                 # pytest configuration
├── conftest.py                # Test fixtures
├── query_viz/                 # Main package
│   ├── __init__.py            # Package initialization
│   ├── core.py                # QueryViz main class
│   ├── query.py               # QueryConfig class
│   ├── database/              # Database connections package
│   │   ├── __init__.py        # Database package init
│   │   ├── base.py            # DatabaseConnection base class
│   │   └── mariadb.py         # MariaDBConnection implementation
│   └── exceptions.py          # Custom exceptions
├── output/                    # Output directory, created by the program
├── tests/                     # Automated tests
└── docker/                    # Files to build Docker containers
    ├── generator              # Generator container (qv-generator)
    ├── web                    # Web application and its container (qv-web)
    ├── docker-compose.yml     # Docker Compose configuration, don't call directly
    ├── start.sh               # Create Docker env
    ├── rebuild.sh             # Recreate existing Docker env
    ├── stop.sh                # Stop and destroy Docker env
    └── test.sh                # Destroy current environment, run tests, show results,
                               # destroy test environment
```


## Copyright and License

Copyright: Vettabase 2025

License: AGPLv3.
