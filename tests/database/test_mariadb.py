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


def test_mariadb_no_initial_status(mariadb_config):
    """Test that MariaDBConnection status is None before we attempt to connect."""
    # Use wrong password
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    assert conn.status is None


@pytest.mark.integration
def test_mariadb_connection_wrong_credentials(mariadb_config):
    """Test that MariaDBConnection fails with wrong credentials."""
    # Use wrong password
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    config['password'] = 'wrong'
    
    conn = MariaDBConnection(config, db_timeout=5)
    
    with pytest.raises(QueryVizError, match=r"\[mariadb\] Failed to create connection pool.*"):
        conn.connect()
    
    assert conn.status == FAIL


@pytest.mark.dependency()
@pytest.mark.integration
def test_mariadb_connection(mariadb_config):
    """Test that MariaDBConnection can establish a connection."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    assert conn.status == SUCCESS
    
    conn.close()


@pytest.mark.dependency(depends=["test_mariadb_connection"])
@pytest.mark.integration
def test_mariadb_connection_close(mariadb_config):
    """Test that MariaDBConnection can properly close its connection pool."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    
    conn.close()
    assert conn.pool is None


def test_mariadb_nothing_to_close(mariadb_config):
    """Test that MariaDBConnection raises an error on close() if no connection was open."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name

    conn = MariaDBConnection(config, db_timeout=5)
    with pytest.raises(QueryVizError, match=r"\[mariadb\] No connection to close.*"):
        conn.close()
    assert conn.pool is None
    assert conn.status is None


def test_mariadb_query_with_no_connection(mariadb_config):
    """Test that MariaDBConnection raises an error on execute_query() if no connection was established."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name

    conn = MariaDBConnection(config, db_timeout=5)
    with pytest.raises(QueryVizError, match=r"\[mariadb\] No connection.*"):
        conn.execute_query('SELECT 1;')
    assert conn.pool is None


@pytest.mark.dependency(depends=["test_mariadb_connection"])
@pytest.mark.integration
def test_mariadb_query_with_syntax_error(mariadb_config):
    """Test that MariaDBConnection raises an error for invalid SQL syntax,
    and this error contains the MariaDB error message."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    
    with pytest.raises(QueryVizError,
            match=r"\[mariadb\] Query execution failed.*You have an error in your SQL syntax.*"
        ):
        conn.execute_query('wrong syntax;')
    
    conn.close()


@pytest.mark.dependency(depends=["test_mariadb_connection"])
@pytest.mark.integration
def test_mariadb_query(mariadb_config):
    """Test that MariaDBConnection can execute a simple query successfully."""
    # Use unique name for this test
    config = mariadb_config.copy()
    config['name'] = inspect.currentframe().f_code.co_name
    
    conn = MariaDBConnection(config, db_timeout=5)
    conn.connect()
    
    columns, results = conn.execute_query('SELECT 1 AS one;')
    
    assert columns == ['one']
    assert len(results) == 1
    assert results[0] == (1,)
    
    conn.close()
