"""Tests for MariaDBConnection."""

import inspect
import os
import pytest
from query_viz.database.mariadb import MariaDBConnection
from query_viz.database.base import SUCCESS, FAIL
from query_viz.exceptions import QueryVizError


@pytest.fixture
def mariadb_config():
    """MariaDB connection configuration from environment variables."""
    return {
        # pools are global and persist between tests
        'name': 'OVERWRITE_ME',
        'dbms': 'mariadb',
        'host': 'qv-test-mariadb',
        'port': 3306,
        'user': os.environ['MYSQL_USER'],
        'password': os.environ['MYSQL_PASSWORD']
    }


@pytest.mark.integration
def test_mariadb_connection_wrong_credentials(mariadb_config):
    """Test that MariaDBConnection fails with wrong credentials."""
    # Use wrong password
    config = mariadb_config.copy()
    config['name'] = current_function_name
    config['password'] = 'wrong'
    
    conn = MariaDBConnection(config, db_timeout=5)
    
    with pytest.raises(QueryVizError, match="Failed to create connection pool"):
        conn.connect()
    
    assert conn.status == FAIL


@pytest.mark.dependency()
@pytest.mark.integration
def test_mariadb_connection(mariadb_config):
    """Test that MariaDBConnection can establish a connection."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = current_function_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    
    assert conn.status == SUCCESS
    
    # Clean up
    conn.close()


@pytest.mark.dependency(depends=["test_mariadb_connection"])
@pytest.mark.integration
def test_mariadb_connection_close(mariadb_config):
    """Test that MariaDBConnection can properly close its connection pool."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = current_function_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    
    # Close connection
    conn.close()
    assert conn.pool is None
