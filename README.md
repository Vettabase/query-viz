# query-viz
A tool to generate real-time charts using Gnuplot.


## Philosophy

Openness: The app is open source.

Interoperability: We aim to support as many database systems as possible.

CaC: We follow the Configuration as Code paradigm. You configure the application using human-readable
configuration files. You can use them to define the queries and the way they are visualised.
The web interface is read-only.

Modularity: The web interface is not necessary to generate the graphs. Each database system support
is implemented in a separate file. Implementing a new one is easy.


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

If you only want to generate Gnuplot charts and don't need a ready-made
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


## Connections and Connectors

Connections are defined in the configuration file. For each query, you define
the Connector to use. Currently available Connectors are:

- MariaDB         (supports on-connection failover on single port, connection pool)
- MySQL           (supports connection pool)
- PostgreSQL      (supports connection pool)

If you are interested in developing a new Connector, see
`query-viz/database/README.md`.


### Obtaining Information About Connectors

Just in case the above list is not up to date, you can obtain the actual list
in this way:

```
./qv.py --list-dbms
```

You can see information about a specific Connector like this:

```
./qv.py --show-dbms MariaDB
```

Currently, Connector names are case-sensitive.

To run the above commands in Docker:

```
docker exec -ti qv-generator /app/qv.py --list-dbms
docker exec -ti qv-generator /app/qv.py --show-dbms MariaDB
```


### Failover and Load Balancing

Connectors that support on-connection failover accept a list of hosts, and will connect
to the first responsive host in the list. The list can include a port (host1:24,host2:42)
but some Connectors require that all hosts use the same port.

Note that failover only happens on connection. After that, no form of failover
is supported.

While the program does no load balancing, you can force load balancing by assigning queries
to different connections.

As far as Query-Viz knows, each connection has a single dedicated thread. However, some
Connectors use a connection pool intrnally, so different queries might actually run
on different connections to the same server.


### Connection Failures

When the program starts, it verifies that at least one connection can be established.
If not, the program cannot do anything useful, so it will exit. The exit code will be 0
on Docker to avoid restart, and it will be 1 on other environments.

Connections fail if they receive an error from the server, or after a timeout with a length
of `failed_connections_interval`.

However, initial connections might take some time, for various reasons. For this reason,
connections have an initial Grace Period. Its length is set via `initial_grace_period`.
During the Grace Period, connections are retried with an interval of
`grace_period_retry_interval`.

After the Grace Period, the program will check if at least one connection is established.
If it decides to continue but at least one connection failed, it will start
a Retry Thread. This thread is responsible for retry connections every
`failed_connections_interval`. When all connections are established, the Retry Thread
exits.

All mentioned intervals can be configured in flexible ways:

```
initial_grace_period: 1.5m           # 90 seconds
failed_connections_interval: 30      # 30 seconds
grace_period_retry_interval: 30s     # 30 seconds
```

## Directory Tree

Query-Viz' directory structure is the following:

```
query-viz/
├── qv.py                      # Main entry point
├── config.yaml.template       # Configuration file template
├── config.yaml                # Configuration file (you should create it!)
├── template.plt               # Gnuplot template
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
