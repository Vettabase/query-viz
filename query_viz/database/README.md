# DBMS Connectors

DBMS Connectors are Python modules that add support for a specific DBMS.

## Listing Available Connectors

To get a list of Connectors:

```
qv.py --list-dbms
```

When using Docker:

```
docker exec -ti qv-generator /app/qv.py --list-dbms
```

## Details About a Connector

To see all details about a Connector:

```
qv.py --show-dbms <connector-name>
```

When using Docker:

```
docker exec -ti qv-generator /app/qv.py --show-dbms <connector-name>
```

## Adding A Connector

To add a Connector, the easiest way is to add a module in this directory.
The module will need to extend `DatabaseConnection`, which is in `base.py`,
and be mentioned in `__init__.py`.

To raise exceptions, make sure to use `QueryVizError` from `..exceptions`.
