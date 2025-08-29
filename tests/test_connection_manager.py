"""Tests for ConnectionManager class"""

import pytest
from query_viz.connection_manager import ConnectionManager
from query_viz.database import MariaDBConnection
from query_viz.exceptions import QueryVizError


@pytest.mark.unit
def test_connection_manager_instantiation():
    """Test that ConnectionManager can be instantiated."""
    manager = ConnectionManager()
    assert manager is not None
    assert isinstance(manager, ConnectionManager)


@pytest.mark.unit
def test_connection_manager_import():
    """Test that ConnectionManager can be imported from main package."""
    from query_viz import ConnectionManager as ImportedConnectionManager
    
    manager = ImportedConnectionManager()
    assert manager is not None
    assert isinstance(manager, ImportedConnectionManager)


@pytest.mark.unit
def test_get_connection_class_mariadb():
    """Test that get_connection_class returns MariaDBConnection for mariadb."""
    conn_class = ConnectionManager.get_connection_class('mariadb')
    assert conn_class is MariaDBConnection


@pytest.mark.unit
def test_get_connection_class_unsupported():
    """Test that get_connection_class raises error for unsupported DBMS."""
    with pytest.raises(QueryVizError, match="Unsupported DBMS: postgresql"):
        ConnectionManager.get_connection_class('postgresql')


@pytest.mark.unit
def test_validate_connection_config_valid():
    """Test that validate_connection_config passes for valid config."""
    config = {
        'name': 'test_db',
        'dbms': 'mariadb',
        'host': 'localhost',
        'port': 3306,
        'user': 'testuser',
        'password': 'testpass'
    }
    
    # Should not raise any exception
    ConnectionManager.validate_connection_config(config, 0)


@pytest.mark.unit
def test_validate_connection_config_missing_field():
    """Test that validate_connection_config raises error for missing required field."""
    config = {
        'name': 'test_db',
        'dbms': 'mariadb',
        'host': 'localhost',
        # Missing port, user, password
    }
    
    with pytest.raises(QueryVizError, match="Connection 0: 'port' is required"):
        ConnectionManager.validate_connection_config(config, 0)


@pytest.mark.unit
def test_validate_connection_config_multiple_missing_fields():
    """Test that validate_connection_config reports first missing field."""
    config = {
        'name': 'test_db',
        # Missing everything else
    }
    
    with pytest.raises(QueryVizError, match="Connection 0: 'dbms' is required"):
        ConnectionManager.validate_connection_config(config, 0)
