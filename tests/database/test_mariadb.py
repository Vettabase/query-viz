"""Tests for MariaDBConnection."""

import os
import pytest
from query_viz.database.mariadb import MariaDBConnection
from query_viz.database.base import SUCCESS


@pytest.fixture
def mariadb_config():
    """MariaDB connection configuration from environment variables."""
    return {
        'name': 'test_mariadb',
        'dbms': 'mariadb',
        'host': 'qv-test-mariadb',
        'port': 3306,
        'user': os.environ['MYSQL_USER'],
        'password': os.environ['MYSQL_PASSWORD']
    }


@pytest.mark.integration
def test_mariadb_connection(mariadb_config):
    """Test that MariaDBConnection can establish a connection."""
    conn = MariaDBConnection(mariadb_config, db_timeout=5)
    conn.connect()
    
    assert conn.status == SUCCESS
    
    # Clean up
    conn.close()
