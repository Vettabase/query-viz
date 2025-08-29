"""Tests for ConnectionManager class"""

import pytest
from unittest.mock import Mock, patch

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

@pytest.mark.unit
def test_setup_connections_for_success():
    """Test that setup_connections_for properly creates connections."""
    manager = ConnectionManager()
    connections_dict = {}
    connections_config = [
        {
            'name': 'test_db1',
            'dbms': 'mariadb',
            'host': 'localhost',
            'port': 3306,
            'user': 'testuser',
            'password': 'testpass'
        },
        {
            'name': 'test_db2',
            'dbms': 'mariadb',
            'host': 'localhost',
            'port': 3307,
            'user': 'testuser',
            'password': 'testpass'
        }
    ]
    db_timeout = 10
    
    default_connection = manager.setup_connections_for(connections_dict, connections_config, db_timeout)
    
    # Check that connections were created
    assert len(connections_dict) == 2
    assert 'test_db1' in connections_dict
    assert 'test_db2' in connections_dict
    assert isinstance(connections_dict['test_db1'], MariaDBConnection)
    assert isinstance(connections_dict['test_db2'], MariaDBConnection)
    
    # Check default connection name
    assert default_connection == 'test_db1'

@pytest.mark.unit
def test_setup_connections_for_invalid_config():
    """Test that setup_connections_for raises error for invalid config."""
    manager = ConnectionManager()
    connections_dict = {}
    connections_config = [
        {
            'name': 'test_db1',
            'dbms': 'mariadb',
            # Missing required fields
        }
    ]
    db_timeout = 10
    
    with pytest.raises(QueryVizError, match="Connection 0: 'host' is required"):
        manager.setup_connections_for(connections_dict, connections_config, db_timeout)


@pytest.mark.unit
@patch('time.sleep')  # Mock sleep to speed up test
@patch('time.time')   # Mock time to control timing
def test_test_connections_for_all_succeed(mock_time, mock_sleep):
    """Test that test_connections_for returns True when all connections succeed."""
    # Mock time progression
    mock_time.side_effect = [0, 0, 0, 0]  # Start time and elapsed time checks
    
    manager = ConnectionManager()
    
    # Create mock connections that succeed
    mock_conn1 = Mock()
    mock_conn1.host = 'host1'
    mock_conn1.connect.return_value = None  # Success
    
    mock_conn2 = Mock()
    mock_conn2.host = 'host2'
    mock_conn2.connect.return_value = None  # Success
    
    connections_dict = {
        'conn1': mock_conn1,
        'conn2': mock_conn2
    }
    
    result = manager.test_connections_for(connections_dict, 60, 5)
    
    assert result is True
    assert mock_conn1.connect.called
    assert mock_conn2.connect.called
    mock_sleep.assert_not_called()  # Should not retry if all succeed

@pytest.mark.unit
@patch('time.sleep')  # Mock sleep to speed up test
@patch('time.time')   # Mock time to control timing
def test_test_connections_for_grace_period_expires(mock_time, mock_sleep):
    """Test that test_connections_for returns False when grace period expires."""
    # Mock time progression: start at 0, then 70 seconds elapsed (past grace period of 60)
    mock_time.side_effect = [0, 0, 70, 70]  # Start time, first check, second check, final check
    
    manager = ConnectionManager()
    
    # Create mock connection that always fails
    mock_conn = Mock()
    mock_conn.host = 'failing_host'
    mock_conn.connect.side_effect = QueryVizError("Connection failed")
    mock_conn.close.return_value = None
    
    connections_dict = {'conn1': mock_conn}
    
    result = manager.test_connections_for(connections_dict, 60, 5)
    
    assert result is False
    assert mock_conn.connect.called
    assert mock_conn.close.called  # Should close failed connections
    mock_sleep.assert_not_called()  # Should not sleep if grace period already expired
